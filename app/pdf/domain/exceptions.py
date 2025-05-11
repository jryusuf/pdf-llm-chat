class PDFDomainError(Exception):
    pass


class PDFNotFoundError(PDFDomainError):
    # def __init__(self, pdf_id: str):
    #     self.pdf_id = pdf_id
    #     super().__init__(f"PDF with ID '{pdf_id}' not found.")
    pass


class PDFNotOwnedError(PDFDomainError):
    # def __init__(self, pdf_id: str, user_id: int):
    #     self.pdf_id = pdf_id
    #     self.user_id = user_id
    #     super().__init__(f"PDF '{pdf_id}' not owned by user '{user_id}'.")
    pass


class PDFAlreadyParsingError(PDFDomainError):
    #  def __init__(self, pdf_id: str):
    #     self.pdf_id = pdf_id
    #     super().__init__(f"PDF '{pdf_id}' is already being parsed or has been parsed.")
    pass


class PDFNotParsedError(PDFDomainError):
    def __init__(self, pdf_id: str):
        self.pdf_id = pdf_id
        super().__init__(f"PDF '{pdf_id}' has not been successfully parsed yet.")

    pass


class InvalidPDFFileTypeError(PDFDomainError):
    # def __init__(self, provided_type: str):
    #     self.provided_type = provided_type
    #     super().__init__(f"Invalid file type: '{provided_type}'. Only 'application/pdf' is accepted.")
    pass
