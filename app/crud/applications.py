from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime

from crud.base import CRUDBase
from models.models import Application
from schemas.applications import ApplicationCreate, ApplicationUpdate

class CRUDApplication(CRUDBase[Application, ApplicationCreate, ApplicationUpdate]):
    def get_by_name(self, db: Session, *, name: str) -> Optional[Application]:
        return db.query(Application).filter(Application.name == name, Application.deleted_at == None).first()
    
    def get_by_user(self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100) -> List[Application]:
        return db.query(Application).filter(
            Application.user_id == user_id,
            Application.deleted_at == None
        ).order_by(desc(self.model.created_at)).all()
    
    def approve(self, db: Session, *, id: int) -> Application:
        db_obj = db.query(Application).filter(Application.id == id, Application.deleted_at == None).first()
        if db_obj:
            db_obj.is_approved = True
            db.commit()
            db.refresh(db_obj)
        return db_obj
    
    def get_by_name(self, db: Session, name: str) -> Optional[Application]:
        return db.query(self.model).filter(self.model.name == name, self.model.deleted_at == None).first()

crud_application = CRUDApplication(Application)