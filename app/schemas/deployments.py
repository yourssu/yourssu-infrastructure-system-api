from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from core.enums import DeploymentState
from schemas.manifests import ManifestBase

class DeploymentBase(BaseModel):
    domain_name: str
    cpu_requests: str
    memory_requests: str
    cpu_limits: str
    memory_limits: str
    port: int
    image_url: str
    replicas: int = 1
    message: Optional[str] = None

class DeploymentCreate(DeploymentBase):
    application_id: int
    
class DeploymentCreateWithManifests(BaseModel):
    link: str
    deployment: DeploymentCreate
    manifests: Optional[List[ManifestBase]]

class DeploymentUpdate(DeploymentBase):
    pass

class DeploymentUpdateWithManifests(BaseModel):
    link: Optional[str]
    deployment: DeploymentUpdate
    manifests: Optional[List[ManifestBase]] = None
    is_request: bool

class DeploymentApprove(BaseModel):
    link: str
    state: DeploymentState
    comment: str = None

class DeploymentImageUpdate(BaseModel):
    application_id: int
    image_url: str
    commit_sha: str

class DeploymentResponse(DeploymentBase):
    id: int
    application_id: int
    comment: Optional[str] = None
    is_applied: bool
    state: DeploymentState
    user_id: int
    admin_id: Optional[int] = None
    manifests: Optional[List[ManifestBase]] = []
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }

class DeploymentPageResponse(BaseModel):
    data: List[DeploymentResponse]
    current_skip: int
    current_limit: int
    total_count: int
    total_pages: int

    model_config = {
        "from_attributes": True
    }