import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from backend.app.models.models import UserRole


class UserBase(BaseModel):
    username: str
    email: str
    role: UserRole = UserRole.OPERATOR
    is_active: bool = True


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: UserRole = UserRole.OPERATOR


class UserUpdate(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
