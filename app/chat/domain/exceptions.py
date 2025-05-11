class ChatDomainError(Exception):
    pass


class NoPDFSelectedForChatError(ChatDomainError):
    pass


class PDFNotParsedForChatError(ChatDomainError):
    pass


class LLMGenerationError(ChatDomainError):
    pass
