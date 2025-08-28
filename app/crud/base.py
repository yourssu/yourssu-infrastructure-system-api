from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from datetime import datetime

from core.database import Base
from core.enums import OrderBy

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        CRUD 객체 생성자
        """
        self.model = model

    def _apply_ordering(self, query, model, order_by: OrderBy):
        if order_by == OrderBy.CREATED_AT_DESC:
            return query.order_by(desc(model.created_at))
        elif order_by == OrderBy.CREATED_AT_ASC:
            return query.order_by(asc(model.created_at))
        elif order_by == OrderBy.UPDATED_AT_DESC:
            return query.order_by(desc(model.updated_at))
        elif order_by == OrderBy.UPDATED_AT_ASC:
            return query.order_by(asc(model.updated_at))
        
        return query

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        return db.query(self.model).filter(self.model.id == id, self.model.deleted_at == None).first()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: OrderBy = OrderBy.CREATED_AT_DESC
    ) -> List[ModelType]:
        query = db.query(self.model).filter(self.model.deleted_at == None)

        if order_by == OrderBy.CREATED_AT_DESC:
            query = query.order_by(desc(self.model.created_at))
        elif order_by == OrderBy.CREATED_AT_ASC:
            query = query.order_by(asc(self.model.created_at))
        elif order_by == OrderBy.UPDATED_AT_DESC:
            query = query.order_by(desc(self.model.updated_at))
        elif order_by == OrderBy.UPDATED_AT_ASC:
            query = query.order_by(asc(self.model.updated_at))

        return query.offset(skip).limit(limit).all()
    
    def create(self, db: Session, *, obj_in: CreateSchemaType, **extra_data) -> ModelType:
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data, **extra_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
            
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        db_obj.updated_at = datetime.now()
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> ModelType:
        obj = db.query(self.model).get(id)
        obj.deleted_at = datetime.now()
        db.commit()
        return obj

    def delete(self, db: Session, *, id: int) -> ModelType:
        obj = db.query(self.model).get(id)
        db.delete(obj)
        db.commit()
        return obj

    def get_count(self, db: Session) -> int:
        return db.query(self.model).filter(self.model.deleted_at == None).count()