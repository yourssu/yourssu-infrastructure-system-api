from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from datetime import datetime

from crud.base import CRUDBase
from core.enums import DeploymentState, OrderBy
from models.models import Deployment
from schemas.deployments import DeploymentCreate, DeploymentUpdate

class CRUDDeployment(CRUDBase[Deployment, DeploymentCreate, DeploymentUpdate]):
    def get_by_application(
        self,
        db: Session,
        *,
        application_id: int,
        skip: int = 0,
        limit: int = 100,
        order_by: OrderBy = OrderBy.CREATED_AT_DESC
    ) -> List[Deployment]:
        query = db.query(Deployment).filter(
            Deployment.application_id == application_id,
            Deployment.deleted_at == None
        )
        query = self._apply_ordering(query, Deployment, order_by)
        return query.offset(skip).limit(limit).all()


    def get_by_user(
        self,
        db: Session,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        order_by: OrderBy = OrderBy.CREATED_AT_DESC
    ) -> List[Deployment]:
        query = db.query(Deployment).filter(
            Deployment.user_id == user_id,
            Deployment.deleted_at == None
        )
        query = self._apply_ordering(query, Deployment, order_by)
        return query.offset(skip).limit(limit).all()


    def get_by_state(
        self,
        db: Session,
        *,
        state: DeploymentState,
        skip: int = 0,
        limit: int = 100,
        order_by: OrderBy = OrderBy.CREATED_AT_DESC
    ) -> List[Deployment]:
        query = db.query(Deployment).filter(
            Deployment.state == state,
            Deployment.deleted_at == None
        )
        query = self._apply_ordering(query, Deployment, order_by)
        return query.offset(skip).limit(limit).all()

    
    def get_applied(self, db: Session, *, application_id: int) -> Optional[Deployment]:
        return db.query(Deployment).filter(
            Deployment.application_id == application_id,
            Deployment.is_applied == True,
            Deployment.deleted_at == None
        ).first()

    def update_applied(self, db: Session, *, id: int, is_applied: bool) -> Deployment:
        db_obj = db.query(Deployment).filter(Deployment.id == id, Deployment.deleted_at == None).first()
        if db_obj:
            db_obj.is_applied = is_applied
            db.commit()
            db.refresh(db_obj)
        return db_obj
    
    def update_state(self, db: Session, *, id: int, admin_id: int, state: str, comment: str = None) -> Deployment:
        db_obj = db.query(Deployment).filter(Deployment.id == id, Deployment.deleted_at == None).first()
        if db_obj:
            db_obj.admin_id = admin_id
            db_obj.state = state
            if state == DeploymentState.APPROVAL:
                db_obj.is_applied = True
            db_obj.comment = comment
            db_obj.updated_at = datetime.now()
            db.commit()
            db.refresh(db_obj)
        return db_obj

crud_deployment = CRUDDeployment(Deployment)