from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from app.pdf.domain.models import PDFDocument, PDFParseStatus
from app.pdf.infrastucture.repositories.pdf_repository import IPDFRepository
from app.pdf.domain.exceptions import PDFNotFoundError
import io
from typing import Optional, Any, List
from datetime import datetime, timezone
from loguru import logger


class MongoPDFRepository(IPDFRepository):
    def __init__(self, db: AsyncIOMotorDatabase, fs: AsyncIOMotorGridFSBucket):
        self.db = db
        self.pdf_meta_collection = db["pdf_metadata_collection"]
        self.parsed_texts_collection = db["parsed_pdf_texts_collection"]
        self.fs = fs

    async def _doc_to_domain(self, doc: dict) -> Optional[PDFDocument]:
        if not doc:
            return None
        return PDFDocument(
            id=str(doc["_id"]),
            user_id=doc["user_id"],
            gridfs_file_id=str(doc["gridfs_file_id"]),
            original_filename=doc["original_filename"],
            upload_date=doc.get("upload_date"),
            parse_status=PDFParseStatus(doc.get("parse_status", "UNPARSED")),
            parse_error_message=doc.get("parse_error_message"),
            is_selected_for_chat=doc.get("is_selected_for_chat", False),
            parsed_text_id=str(doc["parsed_text_id"]) if doc.get("parsed_text_id") else None,
        )

    async def save_pdf_binary(
        self, filename: str, content: bytes, user_id: int, content_type: str = "application/pdf"
    ) -> str:
        gridfs_id = await self.fs.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={"contentType": content_type, "user_id": user_id},
        )
        return str(gridfs_id)

    async def save_pdf_meta(self, pdf_doc: PDFDocument) -> PDFDocument:
        meta_doc = {
            "user_id": pdf_doc.user_id,
            "gridfs_file_id": ObjectId(pdf_doc.gridfs_file_id),
            "original_filename": pdf_doc.original_filename,
            "upload_date": pdf_doc.upload_date,
            "parse_status": pdf_doc.parse_status.value,
            "parse_error_message": pdf_doc.parse_error_message,
            "is_selected_for_chat": pdf_doc.is_selected_for_chat,
            "parsed_text_id": ObjectId(pdf_doc.parsed_text_id) if pdf_doc.parsed_text_id else None,
        }
        result = await self.pdf_meta_collection.insert_one(meta_doc)
        pdf_doc.id = str(result.inserted_id)
        return pdf_doc

    async def get_pdf_meta_by_id(self, pdf_id: str, user_id: int) -> Optional[PDFDocument]:
        try:
            obj_id = ObjectId(pdf_id)
        except Exception:
            return None
        doc = await self.pdf_meta_collection.find_one({"_id": obj_id, "user_id": user_id})
        return await self._doc_to_domain(doc)

    async def get_pdf_binary_stream_by_gridfs_id(
        self, gridfs_id: str
    ) -> Optional[AsyncIOMotorGridFSBucket]:
        try:
            obj_id = ObjectId(gridfs_id)
            grid_out = await self.fs.open_download_stream(obj_id)
            return grid_out
        except Exception:
            return None

    async def get_all_pdf_meta_for_user(
        self, user_id: int, skip: int = 0, limit: int = 20
    ) -> List[PDFDocument]:
        cursor = (
            self.pdf_meta_collection.find({"user_id": user_id})
            .sort("upload_date", -1)
            .skip(skip)
            .limit(limit)
        )
        docs_domain = []
        async for doc in cursor:
            domain_obj = await self._doc_to_domain(doc)
            if domain_obj:
                docs_domain.append(domain_obj)
        return docs_domain

    async def count_all_pdf_meta_for_user(self, user_id: int) -> int:
        return await self.pdf_meta_collection.count_documents({"user_id": user_id})

    async def update_pdf_meta(self, pdf_doc: PDFDocument) -> PDFDocument:
        try:
            obj_id = ObjectId(pdf_doc.id)
        except Exception:
            raise PDFNotFoundError(pdf_id=pdf_doc.id)

        update_data = {
            "parse_status": pdf_doc.parse_status.value,
            "parse_error_message": pdf_doc.parse_error_message,
            "is_selected_for_chat": pdf_doc.is_selected_for_chat,
            "parsed_text_id": ObjectId(pdf_doc.parsed_text_id) if pdf_doc.parsed_text_id else None,
            "upload_date": pdf_doc.upload_date,
        }
        result = await self.pdf_meta_collection.update_one(
            {"_id": obj_id, "user_id": pdf_doc.user_id}, {"$set": update_data}
        )
        if result.matched_count == 0:
            raise PDFNotFoundError(pdf_id=pdf_doc.id)
        return pdf_doc

    async def set_pdf_selected_for_chat(self, user_id: int, pdf_id_to_select: str) -> bool:
        try:
            select_obj_id = ObjectId(pdf_id_to_select)
        except Exception:
            return False

        deselect_result = await self.pdf_meta_collection.update_many(
            {"user_id": user_id, "is_selected_for_chat": True, "_id": {"$ne": select_obj_id}},
            {"$set": {"is_selected_for_chat": False}},
        )

        select_result = await self.pdf_meta_collection.update_one(
            {"_id": select_obj_id, "user_id": user_id}, {"$set": {"is_selected_for_chat": True}}
        )
        return select_result.modified_count > 0 or select_result.matched_count > 0

    async def save_parsed_text(self, pdf_meta_id: str, text_content: str) -> str:
        parsed_text_doc = {
            "pdf_metadata_id": ObjectId(pdf_meta_id),
            "text_content": text_content,
            "created_at": datetime.now(timezone.utc),
        }
        result = await self.parsed_texts_collection.insert_one(parsed_text_doc)
        return str(result.inserted_id)

    async def get_parsed_text_by_pdf_meta_id(self, pdf_meta_id: str) -> Optional[str]:
        try:
            obj_id = ObjectId(pdf_meta_id)
        except Exception:
            return None
        doc = await self.parsed_texts_collection.find_one({"pdf_metadata_id": obj_id})
        return doc["text_content"] if doc else None

    async def get_selected_pdf_for_user(self, user_id: int) -> Optional[PDFDocument]:
        logger.debug(f"Attempting to get selected PDF for user_id: {user_id}")
        doc = await self.pdf_meta_collection.find_one({"user_id": user_id, "is_selected_for_chat": True})
        if doc:
            logger.debug(f"Selected PDF found for user_id: {user_id}, PDF ID: {str(doc['_id'])}")
            return await self._doc_to_domain(doc)
        else:
            logger.debug(f"No PDF selected for chat found for user_id: {user_id}")
            return None
