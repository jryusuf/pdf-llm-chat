async def generate_llm_response_task(
    chat_turn_id: int,
    # These would be provided by Procrastinate's dependency injection/context
    chat_repo: IChatRepository,
    pdf_repo: IPDFRepository,
    settings: Settings,
    llm_client: YourLLMClient,  # Your Gemini client
):
    chat_turn = await chat_repo.get_chat_turn_by_id(chat_turn_id)  # Need user_id too for get_chat_turn
    # The get_chat_turn_by_id might need user_id if it's part of its query logic for security
    # or the task context from Procrastinate might already have user_id.
    # For simplicity, assume chat_turn_id is globally unique enough for task to fetch its details.
    if not chat_turn:  # log error, return
        return

    # Mark as processing
    chat_turn.mark_llm_processing()
    await chat_repo.update_llm_response_in_turn(chat_turn)

    parsed_text = await pdf_repo.get_parsed_text_by_pdf_meta_id(chat_turn.pdf_document_id)
    if not parsed_text:  # log error, mark failed, return
        chat_turn.set_llm_response_failure()  # Or a more specific status
        await chat_repo.update_llm_response_in_turn(chat_turn)
        return

    prompt = parsed_text + "\n\nUser question: " + chat_turn.user_message_content

    # LLM Call with retries
    # response_content = None
    # for attempt in range(settings.LLM_RETRY_ATTEMPTS):
    #     try:
    #         response_content = await llm_client.generate(prompt)
    #         chat_turn.set_llm_response_success(response_content)
    #         break
    #     except Exception as e:
    #         # log e
    #         if attempt == settings.LLM_RETRY_ATTEMPTS - 1:
    #             chat_turn.set_llm_response_failure()
    #
    # await chat_repo.update_llm_response_in_turn(chat_turn)
    pass
