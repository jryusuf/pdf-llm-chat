from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from app.pdf.application.services import PDFApplicationService
from app.pdf.application.schemas import (
    PDFMetadataResponse,
    PaginatedPDFListResponse,
    PDFParseRequest,
    PDFSelectRequest,
    PDFSelectResponse,
)  # Import necessary schemas
from app.account.domain.models import User as UserDomainModel  # Assuming this is the user model type
from app.account.controller.dependencies import (
    get_current_user,
)  # Assuming get_current_user is here or mocked

# Assuming get_pdf_application_service is defined in dependencies.py
from app.pdf.controller.dependencies import get_pdf_application_service
from app.pdf.domain.exceptions import PDFNotParsedError, PDFNotFoundError  # Import necessary exceptions

router = APIRouter()


@router.post("/pdf-upload", response_model=PDFMetadataResponse, status_code=status.HTTP_201_CREATED)
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: UserDomainModel = Depends(get_current_user),  # Authenticated user dependency
    pdf_service: PDFApplicationService = Depends(get_pdf_application_service),  # PDF service dependency
):
    """
    Upload a PDF file and store its metadata.
    """
    # This is the actual endpoint logic.
    # In tests, dependencies (get_current_user, get_pdf_application_service) are mocked.
    # The mock pdf_service.upload_pdf will be called.

    # Basic file type validation (can be more robust)
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only PDF files are allowed."
        )

    # Read file content
    file_content = await file.read()

    # Call the application service to handle the upload
    # The service will interact with the repository (which is also mocked in tests)
    uploaded_pdf_metadata = await pdf_service.upload_pdf(
        current_user_id=int(current_user.user_uuid),  # Pass user ID as integer
        file=file,  # Pass the UploadFile object directly
    )

    return uploaded_pdf_metadata


# Endpoint to list user's PDFs
@router.get("/pdf-list", response_model=PaginatedPDFListResponse)
async def list_pdfs_for_user(
    current_user: UserDomainModel = Depends(get_current_user),  # Authenticated user dependency
    pdf_service: PDFApplicationService = Depends(get_pdf_application_service),  # PDF service dependency
    page: int = 1,  # Pagination: current page (default 1)
    size: int = 10,  # Pagination: items per page (default 10)
):
    """
    Retrieve a paginated list of PDFs uploaded by the authenticated user.
    """
    # Call the application service to handle retrieving the list
    paginated_list = await pdf_service.list_pdfs_for_user(
        current_user_id=int(current_user.user_uuid),  # Pass user ID as integer
        page=page,
        size=size,
    )
    return paginated_list


# Endpoint to initiate PDF parsing
@router.post("/pdf-parse", status_code=status.HTTP_202_ACCEPTED)
async def request_pdf_parsing(
    request: PDFParseRequest,  # Request body containing pdf_id
    current_user: UserDomainModel = Depends(get_current_user),  # Authenticated user dependency
    pdf_service: PDFApplicationService = Depends(get_pdf_application_service),  # PDF service dependency
):
    """
    Initiate asynchronous parsing for a specified PDF.
    """
    # Call the application service to handle the parsing request
    # The service will update status and enqueue the task
    parse_response = await pdf_service.request_pdf_parsing(
        current_user_id=int(current_user.user_uuid),  # Pass user ID as integer
        pdf_id=request.pdf_id,
    )
    # The service returns PDFParseResponse, but the endpoint returns 202 Accepted
    # with no body by default for 202. If a body is needed, response_model should be added.
    # Based on the feature file, only 202 Accepted is explicitly mentioned for the API step.
    # Let's return the service response for now, as it contains useful info,
    # and the schema is defined. Add response_model=PDFParseResponse.
    return parse_response


# Endpoint to select a PDF for chat
@router.post("/pdf-select", response_model=PDFSelectResponse, status_code=status.HTTP_200_OK)
async def select_pdf_for_chat(
    request: PDFSelectRequest,  # Request body containing pdf_id
    current_user: UserDomainModel = Depends(get_current_user),  # Authenticated user dependency
    pdf_service: PDFApplicationService = Depends(get_pdf_application_service),  # PDF service dependency
):
    """
    Select a previously uploaded and parsed PDF to be the context for chat.
    """
    try:
        # Call the application service to handle the selection request
        select_response = await pdf_service.select_pdf_for_chat(
            current_user_id=int(current_user.user_uuid),  # Pass user ID as integer
            pdf_id=request.pdf_id,
        )
        return select_response
    except PDFNotParsedError as e:
        # Catch the specific domain exception and return an HTTP 409 Conflict
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),  # Use the exception message as the detail
        )
    except PDFNotFoundError as e:
        # Catch the specific domain exception and return an HTTP 404 Not Found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),  # Use the exception message as the detail
        )
    # Other potential exceptions might be allowed to propagate for default FastAPI error handling.


# You might have other PDF related endpoints here (e.g., get PDF, list PDFs)
