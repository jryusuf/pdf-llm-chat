from pydantic import BaseModel, EmailStr, Field
import uuid
from datetime import datetime


# --- User Registration ---
class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, description="Password must be at least 8 characters long.")


class UserRegisteredResponse(BaseModel):
    user_uuid: uuid.UUID
    email: EmailStr
    message: str = "User registered successfully."


# --- User Login ---
class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_uuid: uuid.UUID


# --- User Info (example for authenticated user context) ---
class UserInDB(BaseModel):
    id: int
    user_uuid: uuid.UUID
    email: EmailStr
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True
