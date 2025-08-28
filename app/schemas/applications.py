from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from schemas.users import UserBase

class ApplicationBase(BaseModel):
    description: str

class ApplicationCreate(ApplicationBase):
    name: str

class ApplicationUpdate(ApplicationBase):
    pass

class ApplicationResponse(ApplicationBase):
    id: int
    name: str
    user: UserBase
    applied_deployment_id: Optional[int] = None # TODO: 추후 삭제
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }

class DeploymentStateCount(BaseModel):
    request_count: int
    check_count: int
    return_count: int
    approval_count: int

class ApplicationResponses(BaseModel):
    data: List[ApplicationResponse]
    state_count: DeploymentStateCount
    current_skip: int
    current_limit: int
    total_count: int
    total_pages: int

    model_config = {
        "from_attributes": True
    }

class ApplicationUniqueRequest(BaseModel):
    name: str

class ApplicationUniqueResponse(BaseModel):
    is_unique: bool