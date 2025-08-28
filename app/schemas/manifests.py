from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ManifestBase(BaseModel):
    file_name: str
    content: str

class ManifestCreate(ManifestBase):
    deployment_id: int

class ManifestUpdate(ManifestBase):
    pass

class ManifestResponse(ManifestBase):
    id: int
    deployment_id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }