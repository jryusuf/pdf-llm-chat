import asyncio
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.main import app  # Assuming the PDF router is included in the main app
from app.pdf.infrastucture.repositories.pdf_repository import IPDFRepository
from app.pdf.application.services import PDFApplicationService
from app.pdf.tests.integration.test_pdf_service_integration import MockPDFRepository, MockDeferParseTask
from app.account.controller.dependencies import get_current_user  # Import the actual dependency to override
from app.account.domain.models import User as UserDomainModel  # Import UserDomainModel
from app.pdf.controller.dependencies import (
    get_pdf_repository,
    get_pdf_application_service,  # Import get_pdf_application_service
)  # Import the PDF repository dependency to override


# Use a global event loop for the test environment
# Will be created in before_all hook


def before_all(context):
    """Set up the test environment before all scenarios."""
    context.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(context.loop)

    # Create instances of the mock repository and service
    context.pdf_repo = MockPDFRepository()
    context.defer_parse_task = MockDeferParseTask()  # Mock the defer task callable
    context.pdf_service = PDFApplicationService(
        pdf_repo=context.pdf_repo,
        settings=MagicMock(),  # Mock settings object
        defer_parse_task=context.defer_parse_task,
    )

    # Override dependencies in the main FastAPI app for testing
    # Override the PDF application service dependency (if used directly in routers)
    # app.dependency_overrides[PDFApplicationService] = lambda: context.pdf_service

    # Create TestClient here using the main app. Dependency overrides will be
    # applied before each scenario.
    context.client = TestClient(app)

    # The defer_parse_task dependency override will be set in before_scenario


def after_all(context):
    """Clean up the test environment after all scenarios."""
    # TestClient does not have a shutdown method
    context.loop.close()
    asyncio.set_event_loop(None)  # Unset the event loop

    # Clear dependency overrides
    app.dependency_overrides = {}


def before_scenario(context, scenario):
    """Set up before each scenario."""
    # Reset the mock repository state before each scenario, passing the context
    context.pdf_repo = MockPDFRepository(context=context)
    context.defer_parse_task = MockDeferParseTask()
    context.pdf_service = PDFApplicationService(
        pdf_repo=context.pdf_repo, settings=MagicMock(), defer_parse_task=context.defer_parse_task
    )

    # Apply dependency overrides for the new mock instances
    # Override the get_pdf_repository dependency to return the mock repository
    app.dependency_overrides[get_pdf_repository] = lambda: context.pdf_repo
    # Override the PDF application service dependency provider
    # This ensures the service uses the scenario-specific mock repository and defer task.
    app.dependency_overrides[get_pdf_application_service] = lambda: PDFApplicationService(
        pdf_repo=context.pdf_repo,
        settings=MagicMock(),  # Use a mock settings object
        defer_parse_task=context.defer_parse_task,
    )

    # Override the get_current_user dependency to simulate authentication
    # This lambda will be called by FastAPI's dependency injection system.
    # It should return a mock UserDomainModel object with the user_id from context.
    def mock_get_current_user():
        if hasattr(context, "user_id") and context.user_id is not None:
            # Create a mock UserDomainModel object
            mock_user = MagicMock(spec=UserDomainModel)
            # Assuming the UserDomainModel has a user_uuid attribute for the ID
            mock_user.user_uuid = context.user_id
            # Add other attributes if needed by the application logic
            # mock_user.email = "test@example.com"
            return mock_user
        else:
            # If user is not authenticated, raise HTTPException 401
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

    app.dependency_overrides[get_current_user] = mock_get_current_user

    # Create a new TestClient for each scenario (optional, but can help isolate tests)
    # Re-creating the client here ensures it picks up the dependency overrides for the scenario
    context.client = TestClient(app)

    # Ensure user_id is cleared for scenarios that don't require authentication
    # This logic might be better handled by explicitly setting context.user_id = None
    # in scenarios that require no authentication, or by using tags.
    # For now, let's rely on the 'Given a user is authenticated' step to set user_id.
    # We will explicitly set user_id = None in scenarios that require no auth.
    pass  # No need to clear user_id here, handle in steps or specific scenario setup


def after_scenario(context, scenario):
    """Clean up after each scenario."""
    # Clear dependency overrides after each scenario
    app.dependency_overrides = {}
    # Clear user_id from context
    if hasattr(context, "user_id"):
        del context.user_id


# Optional: Add before_feature/after_feature hooks if needed
# def before_feature(context, feature):
#     pass

# def after_feature(context, feature):
#     pass

# Optional: Add before_feature/after_feature hooks if needed
# def before_feature(context, feature):
#     pass

# def after_feature(context, feature):
#     pass
