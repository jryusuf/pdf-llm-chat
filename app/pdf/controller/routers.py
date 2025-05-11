from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from app.pdf.application.services import PDFApplicationService
from app.pdf.application.schemas import PDFMetadataResponse
from app.account.domain.models import User as UserDomainModel  # Assuming this is the user model type
from app.account.controller.dependencies import (
    get_current_user,
)  # Assuming get_current_user is here or mocked

# Assuming get_pdf_application_service is defined in dependencies.py
from app.pdf.controller.dependencies import get_pdf_application_service

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


# You might have other PDF related endpoints here (e.g., get PDF, list PDFs)
