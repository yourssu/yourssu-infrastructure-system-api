# app/schemas/data.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PodStatus(BaseModel):
    name: str
    ready: bool
    status: str
    restarts: int
    age: str
    
class DeploymentStatus(BaseModel):
    application_id: int
    name: str
    ready_replicas: int
    total_replicas: int
    available_replicas: int
    updated_replicas: int
    conditions: List[dict]
    pods: List[PodStatus]
    age: str

class DeploymentStatusPage(BaseModel):
    data: List[DeploymentStatus]
    current_skip: int
    current_limit: int
    total_count: int
    total_pages: int

    model_config = {
        "from_attributes": True
    }