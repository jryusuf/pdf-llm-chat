import json
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone
import subprocess

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db_session
from app.core.database_mongo import get_mongo_db

from app.chat.infrastructure.repositories.chat_repository import IChatRepository
from app.chat.infrastructure.repositories.sqlalchmey_chat_repository import SQLAlchemyChatRepository
from app.chat.application.services import ChatApplicationService, DeferLLMTaskType
from app.chat.domain.models import LLMResponseStatus, ChatMessageTurn

from app.pdf.infrastucture.repositories.pdf_repository import IPDFRepository
from app.pdf.infrastucture.repositories.mongo_pdf_repository import MongoPDFRepository
from app.pdf.domain.exceptions import PDFNotFoundError

from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from typing import Optional, Any, Coroutine, Callable


async def _defer_llm_task(
    chat_turn_id: int,
    user_id: int,
    chat_repo: IChatRepository,
    pdf_repo: IPDFRepository,
    settings: Settings,
):
    """
    Background task to defer LLM response generation using Google Gemini API via curl.
    """
    chat_turn = None
    try:
        chat_turn: Optional[ChatMessageTurn] = await chat_repo.get_chat_turn_by_id(
            turn_id=chat_turn_id, user_id=user_id
        )

        if not chat_turn:
            print(f"Error: Chat turn with ID {chat_turn_id} not found for user {user_id}.")
            return

        user_message = chat_turn.user_message_content
        pdf_document_id = chat_turn.pdf_document_id

        parsed_pdf_text: Optional[str] = await pdf_repo.get_parsed_text_by_pdf_meta_id(
            pdf_meta_id=pdf_document_id
        )

        if not parsed_pdf_text:
            print(f"Error: Parsed text not found for PDF ID {pdf_document_id}.")
            chat_turn.llm_response_status = LLMResponseStatus.FAILED
            chat_turn.llm_response_content = "Error: Could not retrieve parsed PDF content."
            await chat_repo.update_llm_response_in_turn(chat_turn)
            return

        gemini_api_key = settings.GEMINI_API_KEY
        system_prompt_text = settings.GEMINI_SYSTEM_PROMPT

        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_api_key}"

        request_payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"Document Content:\n{parsed_pdf_text}"},
                        {"text": f"User Query:\n{user_message}"},
                    ]
                }
            ],
            "generationConfig": {"candidateCount": 1, "temperature": 0.7},
            "systemInstruction": {"parts": [{"text": system_prompt_text}]},
        }
        payload_json = json.dumps(request_payload)

        curl_command = [
            "curl",
            "-H",
            "Content-Type: application/json",
            "-X",
            "POST",
            "-d",
            payload_json,
            api_url,
            "-s",
            "-w",
            "%{http_code}",
        ]

        try:
            process = subprocess.run(curl_command, capture_output=True, text=True, check=False)

            output_with_code = process.stdout
            http_code_str = ""
            curl_output_body = ""

            if len(output_with_code) >= 3:
                http_code_str = output_with_code[-3:]
                curl_output_body = output_with_code[:-3].strip()
                try:
                    http_code = int(http_code_str)
                except ValueError:
                    http_code = -1
            else:
                http_code = -1
                curl_output_body = output_with_code.strip()

            if process.returncode != 0 or not (200 <= http_code < 300):
                error_message = (
                    f"curl command failed. Exit code: {process.returncode}, "
                    f"HTTP code: {http_code_str}. "
                    f"Response: {curl_output_body}. Stderr: {process.stderr.strip()}"
                )
                print(error_message)
                chat_turn.llm_response_status = LLMResponseStatus.FAILED
                chat_turn.llm_response_content = f"LLM Error: {error_message}"
                await chat_repo.update_llm_response_in_turn(chat_turn)
                return

            response_data = json.loads(curl_output_body)

            if (
                response_data.get("candidates")
                and isinstance(response_data["candidates"], list)
                and len(response_data["candidates"]) > 0
                and response_data["candidates"][0].get("content")
                and response_data["candidates"][0]["content"].get("parts")
                and isinstance(response_data["candidates"][0]["content"]["parts"], list)
                and len(response_data["candidates"][0]["content"]["parts"]) > 0
                and response_data["candidates"][0]["content"]["parts"][0].get("text")
            ):
                generated_text = response_data["candidates"][0]["content"]["parts"][0]["text"]
            elif response_data.get("error"):
                api_error = response_data["error"]
                error_message = f"Gemini API Error: {api_error.get('message', 'Unknown error')}"
                print(error_message)
                chat_turn.llm_response_status = LLMResponseStatus.FAILED
                chat_turn.llm_response_content = f"LLM Error: {error_message}"
                await chat_repo.update_llm_response_in_turn(chat_turn)
                return
            else:
                error_message = (
                    f"Could not extract text from Gemini API response. Response: {curl_output_body}"
                )
                print(error_message)
                chat_turn.llm_response_status = LLMResponseStatus.FAILED
                chat_turn.llm_response_content = f"LLM Error: {error_message}"
                await chat_repo.update_llm_response_in_turn(chat_turn)
                return

        except json.JSONDecodeError as e:
            error_message = (
                f"Error decoding JSON response from Gemini API: {e}. Response: {curl_output_body}"
            )
            print(error_message)
            chat_turn.llm_response_status = LLMResponseStatus.FAILED
            chat_turn.llm_response_content = f"LLM Error: {error_message}"
            await chat_repo.update_llm_response_in_turn(chat_turn)
            return
        except Exception as e:
            error_message = f"Error processing Gemini API call: {e}"
            print(error_message)
            chat_turn.llm_response_status = LLMResponseStatus.FAILED
            chat_turn.llm_response_content = f"LLM Error: {error_message}"
            await chat_repo.update_llm_response_in_turn(chat_turn)
            return

        chat_turn.llm_response_content = generated_text
        chat_turn.llm_response_status = LLMResponseStatus.COMPLETED_SUCCESS
        chat_turn.llm_response_timestamp = datetime.now(timezone.utc)

        await chat_repo.update_llm_response_in_turn(chat_turn)

    except Exception as e:
        error_message = f"An unexpected error occurred during LLM task for chat turn {chat_turn_id}: {e}"
        print(error_message)
        if chat_turn:
            chat_turn.llm_response_status = LLMResponseStatus.FAILED_RETRIES_EXHAUSTED
            chat_turn.llm_response_content = f"LLM Error: {error_message}"
            await chat_repo.update_llm_response_in_turn(chat_turn)


def get_chat_repository(session: AsyncSession = Depends(get_db_session)) -> IChatRepository:
    return SQLAlchemyChatRepository(session=session)


async def get_pdf_repository_for_chat_service(
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> IPDFRepository:
    fs = AsyncIOMotorGridFSBucket(db, bucket_name="pdf_binaries")
    return MongoPDFRepository(db=db, fs=fs)


async def get_chat_application_service(
    chat_repo: IChatRepository = Depends(get_chat_repository),
    pdf_repo: IPDFRepository = Depends(get_pdf_repository_for_chat_service),
    settings: Settings = Depends(get_settings),
) -> ChatApplicationService:
    async def actual_defer_llm_task(chat_turn_id: int, user_id: int):
        await _defer_llm_task(chat_turn_id, user_id, chat_repo, pdf_repo, settings)

    return ChatApplicationService(
        chat_repo=chat_repo, pdf_repo=pdf_repo, settings=settings, defer_llm_task=actual_defer_llm_task
    )
