from typing import List, Optional
from sqlalchemy.orm import Session

from crud.base import CRUDBase
from models.models import Template
from schemas.templates import TemplateCreate, TemplateUpdate

class CRUDTemplate(CRUDBase[Template, TemplateCreate, TemplateUpdate]):
    def get_by_name(self, db: Session, *, file_name: str) -> Optional[Template]:
        return db.query(Template).filter(Template.file_name == file_name, Template.deleted_at == None).first()

crud_template = CRUDTemplate(Template)