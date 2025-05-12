from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session

from app.core.config import get_settings
from app.account.application.services import AccountApplicationService
from app.account.application.schemas import (
    UserCreateRequest,
    UserRegisteredResponse,
    UserLoginRequest,
    TokenResponse,
)
from app.account.infrastructure.repositories.user_repository import IUserRepository
from app.account.infrastructure.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from app.account.domain.exceptions import (
    UserAlreadyExistsError,
    InvalidCredentialsError,
)
from loguru import logger


def get_user_repository(
    session: AsyncSession = Depends(get_db_session),
) -> IUserRepository:
    return SQLAlchemyUserRepository(session)


def get_account_application_service(
    user_repo: IUserRepository = Depends(get_user_repository),
) -> AccountApplicationService:
    settings = get_settings()
    return AccountApplicationService(user_repo=user_repo, settings=settings)


router = APIRouter()


@router.post(
    "/register",
    response_model=UserRegisteredResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user_endpoint(
    user_data: UserCreateRequest,
    account_service: AccountApplicationService = Depends(get_account_application_service),
):
    logger.info(f"Received request to register user with email: {user_data.email}")
    try:
        registered_user = await account_service.register_user(user_data)
        logger.info(f"User registration successful for email: {user_data.email}")
        return registered_user
    except UserAlreadyExistsError as e:
        logger.warning(f"User registration failed, user already exists: {user_data.email}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        logger.error(f"User registration failed due to ValueError: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("An unexpected error occurred during user registration.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration.",
        )


@router.post("/login", response_model=TokenResponse)
async def login_for_access_token_endpoint(
    login_data: UserLoginRequest,
    account_service: AccountApplicationService = Depends(get_account_application_service),
):
    logger.info(f"Received login request for email: {login_data.email}")
    try:
        token_response = await account_service.login_user(login_data)
        logger.info(f"User login successful for email: {login_data.email}")
        return token_response
    except InvalidCredentialsError:
        logger.warning(f"Invalid credentials for login attempt: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.exception("An unexpected error occurred during user login.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login.",
        )
