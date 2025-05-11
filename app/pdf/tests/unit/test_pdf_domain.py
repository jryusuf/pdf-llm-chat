import pytest
from datetime import datetime, timezone
from app.pdf.domain.models import PDFDocument, PDFParseStatus
from app.pdf.domain.exceptions import PDFNotParsedError


# Helper function to create a basic PDFDocument instance
def create_basic_pdf_document(
    id="test_id",
    user_id=1,
    gridfs_file_id="gridfs_id",
    original_filename="test.pdf",
    upload_date=None,
    parse_status=PDFParseStatus.UNPARSED,
    parse_error_message=None,
    is_selected_for_chat=False,
    parsed_text_id=None,
):
    return PDFDocument(
        id=id,
        user_id=user_id,
        gridfs_file_id=gridfs_file_id,
        original_filename=original_filename,
        upload_date=upload_date,
        parse_status=parse_status,
        parse_error_message=parse_error_message,
        is_selected_for_chat=is_selected_for_chat,
        parsed_text_id=parsed_text_id,
    )


# Test cases for PDFDocument initialization
def test_pdf_document_initialization_defaults():
    doc = create_basic_pdf_document()
    assert doc.id == "test_id"
    assert doc.user_id == 1
    assert doc.gridfs_file_id == "gridfs_id"
    assert doc.original_filename == "test.pdf"
    assert isinstance(doc.upload_date, datetime)
    assert doc.parse_status == PDFParseStatus.UNPARSED
    assert doc.parse_error_message is None
    assert doc.is_selected_for_chat is False
    assert doc.parsed_text_id is None


def test_pdf_document_initialization_custom_values():
    upload_dt = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    doc = create_basic_pdf_document(
        id="custom_id",
        user_id=10,
        gridfs_file_id="custom_gridfs_id",
        original_filename="custom.pdf",
        upload_date=upload_dt,
        parse_status=PDFParseStatus.PARSED_FAILURE,
        parse_error_message="Failed",
        is_selected_for_chat=True,
        parsed_text_id="parsed_text_123",
    )
    assert doc.id == "custom_id"
    assert doc.user_id == 10
    assert doc.gridfs_file_id == "custom_gridfs_id"
    assert doc.original_filename == "custom.pdf"
    assert doc.upload_date == upload_dt
    assert doc.parse_status == PDFParseStatus.PARSED_FAILURE
    assert doc.parse_error_message == "Failed"
    assert doc.is_selected_for_chat is True
    assert doc.parsed_text_id == "parsed_text_123"


# Test cases for state transition methods
def test_mark_as_parsing():
    doc = create_basic_pdf_document()
    doc.mark_as_parsing()
    assert doc.parse_status == PDFParseStatus.PARSING
    assert doc.parse_error_message is None


def test_mark_as_parsing_from_failure():
    doc = create_basic_pdf_document(
        parse_status=PDFParseStatus.PARSED_FAILURE, parse_error_message="Old error"
    )
    doc.mark_as_parsing()
    assert doc.parse_status == PDFParseStatus.PARSING
    assert doc.parse_error_message is None


def test_mark_parse_success():
    doc = create_basic_pdf_document(parse_status=PDFParseStatus.PARSING)
    parsed_id = "new_parsed_text_id"
    doc.mark_parse_success(parsed_id)
    assert doc.parse_status == PDFParseStatus.PARSED_SUCCESS
    assert doc.parsed_text_id == parsed_id
    assert doc.parse_error_message is None


def test_mark_parse_failure():
    doc = create_basic_pdf_document(parse_status=PDFParseStatus.PARSING)
    error_msg = "Parsing failed due to XYZ"
    doc.mark_parse_failure(error_msg)
    assert doc.parse_status == PDFParseStatus.PARSED_FAILURE
    assert doc.parse_error_message == error_msg
    assert doc.parsed_text_id is None  # Ensure parsed_text_id is reset or remains None on failure


# Test cases for chat selection methods
def test_select_for_chat_success():
    doc = create_basic_pdf_document(parse_status=PDFParseStatus.PARSED_SUCCESS)
    doc.select_for_chat()
    assert doc.is_selected_for_chat is True


def test_select_for_chat_raises_error_if_not_parsed():
    doc_unparsed = create_basic_pdf_document(parse_status=PDFParseStatus.UNPARSED)
    doc_parsing = create_basic_pdf_document(parse_status=PDFParseStatus.PARSING)
    doc_failure = create_basic_pdf_document(parse_status=PDFParseStatus.PARSED_FAILURE)

    with pytest.raises(PDFNotParsedError):
        doc_unparsed.select_for_chat()

    with pytest.raises(PDFNotParsedError):
        doc_parsing.select_for_chat()

    with pytest.raises(PDFNotParsedError):
        doc_failure.select_for_chat()


def test_deselect_for_chat():
    doc = create_basic_pdf_document(is_selected_for_chat=True)
    doc.deselect_for_chat()
    assert doc.is_selected_for_chat is False


# Test cases for PDFParseStatus enum
def test_pdf_parse_status_enum_values():
    assert PDFParseStatus.UNPARSED.value == "UNPARSED"
    assert PDFParseStatus.PARSING.value == "PARSING"
    assert PDFParseStatus.PARSED_SUCCESS.value == "PARSED_SUCCESS"
    assert PDFParseStatus.PARSED_FAILURE.value == "PARSED_FAILURE"
