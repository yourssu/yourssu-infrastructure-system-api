from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

from core.enums import UserRole, UserPart

class UserBase(BaseModel):
    email: EmailStr
    nickname: str
    part: UserPart
    avatar_id: int

    model_config = {
        "from_attributes": True
    }

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    pass

class UserResponse(UserBase):
    id: int
    role: UserRole
    accesses: List[str]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    is_active: bool

    model_config = {
        "from_attributes": True
    }

class UserPageResponse(BaseModel):
    data: List[UserResponse]
    current_skip: int
    current_limit: int
    total_count: int
    total_pages: int

    model_config = {
        "from_attributes": True
    }