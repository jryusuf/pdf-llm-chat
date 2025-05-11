class ChatDomainError(Exception):
    pass


class NoPDFSelectedForChatError(ChatDomainError):
    pass


class PDFNotParsedForChatError(ChatDomainError):
    def __init__(
        self, pdf_id: str | None = None, message: str = "Selected PDF is not successfully parsed for chat."
    ):
        self.pdf_id = pdf_id
        super().__init__(message + (f" PDF ID: {pdf_id}" if pdf_id else ""))


class LLMGenerationError(ChatDomainError):
    pass
