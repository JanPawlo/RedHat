from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.const.auth import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH, TOKEN_TYPE


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
    full_name: Optional[str] = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = TOKEN_TYPE
    expires_in: int
    user: UserResponse
