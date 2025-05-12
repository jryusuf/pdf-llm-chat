from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from app.pdf.application.services import PDFApplicationService
from app.pdf.application.schemas import (
    PDFMetadataResponse,
    PaginatedPDFListResponse,
    PDFParseRequest,
    PDFSelectRequest,
    PDFSelectResponse,
)
from app.lib.security import (
    AuthenticatedUser,
    get_current_authenticated_user,
)

from app.pdf.controller.dependencies import get_pdf_application_service
from app.pdf.domain.exceptions import PDFNotParsedError, PDFNotFoundError
from loguru import logger

router = APIRouter()


@router.post("/pdf-upload", response_model=PDFMetadataResponse, status_code=status.HTTP_201_CREATED)
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_authenticated_user),
    pdf_service: PDFApplicationService = Depends(get_pdf_application_service),
):
    """
    Upload a PDF file and store its metadata.
    """
    logger.info(f"Received request to upload PDF: {file.filename} for user: {current_user.id}")

    if file.content_type != "application/pdf":
        logger.warning(f"Unsupported media type for PDF upload: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only PDF files allowed."
        )

    try:
        uploaded_pdf_metadata = await pdf_service.upload_pdf(
            current_user_id=current_user.id,
            file=file,
        )
        logger.info(f"PDF uploaded successfully: {uploaded_pdf_metadata.id} for user: {current_user.id}")
        return uploaded_pdf_metadata
    except Exception as e:
        logger.exception(f"Error during PDF upload for user {current_user.id}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred during PDF upload."
        )


@router.get("/pdf-list", response_model=PaginatedPDFListResponse)
async def list_pdfs_for_user(
    current_user: AuthenticatedUser = Depends(get_current_authenticated_user),
    pdf_service: PDFApplicationService = Depends(get_pdf_application_service),
    page: int = 1,
    size: int = 10,
):
    """
    Retrieve a paginated list of PDFs uploaded by the authenticated user.
    """
    logger.info(f"Received request to list PDFs for user: {current_user.id}, page: {page}, size: {size}")
    try:
        paginated_list = await pdf_service.list_pdfs_for_user(
            current_user_id=current_user.id,
            page=page,
            size=size,
        )
        logger.info(f"Successfully listed PDFs for user: {current_user.id}")
        return paginated_list
    except Exception as e:
        logger.exception(f"Error listing PDFs for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while listing PDFs.",
        )


@router.post("/pdf-parse", status_code=status.HTTP_202_ACCEPTED)
async def request_pdf_parsing(
    request: PDFParseRequest,
    current_user: AuthenticatedUser = Depends(get_current_authenticated_user),
    pdf_service: PDFApplicationService = Depends(get_pdf_application_service),
):
    """
    Initiate asynchronous parsing for a specified PDF.
    """
    logger.info(f"Received request to parse PDF: {request.pdf_id} for user: {current_user.id}")
    try:
        parse_response = await pdf_service.request_pdf_parsing(
            current_user_id=current_user.id,
            pdf_id=request.pdf_id,
        )

        logger.info(f"PDF parsing initiated for PDF: {request.pdf_id}, user: {current_user.id}")
        return parse_response
    except PDFNotFoundError as e:
        logger.warning(f"PDF not found for parsing: {request.pdf_id}, user: {current_user.id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception(f"Error requesting PDF parsing for PDF: {request.pdf_id}, user: {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while requesting PDF parsing.",
        )


@router.post("/pdf-select", response_model=PDFSelectResponse, status_code=status.HTTP_200_OK)
async def select_pdf_for_chat(
    request: PDFSelectRequest,
    current_user: AuthenticatedUser = Depends(get_current_authenticated_user),
    pdf_service: PDFApplicationService = Depends(get_pdf_application_service),
):
    """
    Select a previously uploaded and parsed PDF to be the context for chat.
    """
    logger.info(f"Received request to select PDF: {request.pdf_id} for chat for user: {current_user.id}")
    try:
        select_response = await pdf_service.select_pdf_for_chat(
            current_user_id=current_user.id,
            pdf_id=request.pdf_id,
        )
        logger.info(f"PDF selected for chat: {request.pdf_id}, user: {current_user.id}")
        return select_response
    except PDFNotParsedError as e:
        logger.warning(
            f"Attempt to select not parsed PDF for chat: {request.pdf_id}, user: {current_user.id}"
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except PDFNotFoundError as e:
        logger.warning(f"PDF not found for selection: {request.pdf_id}, user: {current_user.id}")

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Error selecting PDF for chat: {request.pdf_id}, user: {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while selecting PDF for chat.",
        )
