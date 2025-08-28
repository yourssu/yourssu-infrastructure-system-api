from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from fastapi.encoders import jsonable_encoder
from datetime import datetime

from crud.base import CRUDBase
from models.models import User
from schemas.users import UserCreate, UserUpdate

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email, User.deleted_at == None).first()
    
    def get_by_role(self, db: Session, *, role: str) -> List[User]:
        return db.query(User).filter(User.role == role, User.deleted_at == None).all()
    
    def add_user_access(
        self,
        db: Session,
        *,
        user: User,
        access_to_add: str
    ) -> User:
        # Create a new list instead of modifying in place
        current_accesses = user.accesses.copy() if user.accesses else []
        current_accesses.append(access_to_add)
        user.accesses = list(set(current_accesses))
        user.updated_at = datetime.now()
        
        flag_modified(user, "accesses")
        
        db.commit()
        db.refresh(user)
        return user

    def remove_user_access(
        self,
        db: Session,
        *,
        user: User,
        access_to_remove: str
    ) -> None:
        user_accesses: List[str] = user.accesses
        if access_to_remove in user_accesses:
            user_accesses.remove(access_to_remove)
        user.accesses = user_accesses

        flag_modified(user, "accesses")

        user.updated_at = datetime.now()
        db.commit()
        db.refresh(user)
        return user
    
    def activate(self, db: Session, *, user: User) -> User:
        user.is_active = True
        user.updated_at = datetime.now()
        db.commit()
        db.refresh(user)
        return user
    
crud_user = CRUDUser(User)