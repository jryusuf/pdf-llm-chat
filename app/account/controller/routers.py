from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session

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


def get_user_repository(
    session: AsyncSession = Depends(get_db_session),
) -> IUserRepository:
    return SQLAlchemyUserRepository(session)


def get_account_application_service(
    user_repo: IUserRepository = Depends(get_user_repository),
) -> AccountApplicationService:
    return AccountApplicationService(user_repo=user_repo)


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
    try:
        registered_user = await account_service.register_user(user_data)
        return registered_user
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration.",
        )


@router.post("/login", response_model=TokenResponse)
async def login_for_access_token_endpoint(
    login_data: UserLoginRequest,
    account_service: AccountApplicationService = Depends(get_account_application_service),
):
    try:
        token_response = await account_service.login_user(login_data)
        return token_response
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login.",
        )
