from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from core.database import get_db
from core.enums import OrderBy
from crud.users import crud_user
from crud.applications import crud_application
from schemas.users import UserUpdate, UserResponse, UserPageResponse
from schemas.applications import ApplicationResponse
from core.security import get_current_user_id, verify_token, verify_admin, oauth2_scheme

router = APIRouter()

@router.get("/", response_model=UserPageResponse)
def read_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    order_by: OrderBy = OrderBy.CREATED_AT_DESC,
    token: str = Depends(oauth2_scheme),
):
    """
    사용자 목록 조회
    """
    verify_token(token, db)
    users = crud_user.get_multi(db, skip=skip, limit=limit, order_by=order_by)
    total_count = crud_user.get_count(db)
    total_pages = (total_count + limit - 1) // limit if limit > 0 else 0

    # ORM 모델을 Pydantic 모델로 변환
    user_responses = []
    for user in users:
        # 각 user 항목을 UserResponse로 변환
        user_dict = {
            # UserBase 필드
            "email": user.email,
            "nickname": user.nickname,
            "part": user.part,
            "avatar_id": user.avatar_id,
            
            # UserResponse 추가 필드
            "id": user.id,
            "role": user.role,
            "accesses": user.accesses,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "deleted_at": user.deleted_at,
            "is_active": user.is_active
        }
        
        user_responses.append(UserResponse(**user_dict))

    return UserPageResponse(
        data=user_responses,
        current_skip=skip,
        current_limit=limit,
        total_count=total_count,
        total_pages=total_pages
    )

@router.get("/{user_id}", response_model=UserResponse)
def read_user(
    *,
    db: Session = Depends(get_db),
    user_id: int = Path(..., gt=0),
    token: str = Depends(oauth2_scheme),
):
    """
    사용자 조회
    """
    verify_token(token, db)

    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    return user

@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    *,
    db: Session = Depends(get_db),
    user_in: UserUpdate,
    token: str = Depends(oauth2_scheme)
):
    """
    사용자 정보 수정
    """
    verify_token(token, db)

    if user_in.avatar_id > 12 or user_in.avatar_id < 1:
        raise HTTPException(status_code=400, detail="잘못된 아바타 ID입니다.")

    user_id = get_current_user_id(token, db)
    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    return crud_user.update(db, db_obj=user, obj_in=user_in)

@router.delete("/{user_id}", response_model=UserResponse)
def delete_user(
    *,
    db: Session = Depends(get_db),
    user_id: int = Path(..., gt=0),
    token: str = Depends(oauth2_scheme)
):
    """
    사용자 삭제 (소프트 삭제)
    """
    verify_token(token, db)
    verify_admin(token, db)
    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    applications = crud_application.get_by_user(db, user_id=user_id)
    if applications:
        raise HTTPException(status_code=400, detail="사용자가 관리 중인 애플리케이션이 있습니다.")

    return crud_user.remove(db, id=user_id)

@router.get("/{user_id}/applications", response_model=List[ApplicationResponse])
def read_user_applications(
    *,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """
    사용자가 생성한 애플리케이션 목록 조회
    """
    verify_token(token, db)
    user_id = get_current_user_id(token, db)

    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    return crud_application.get_by_user(db, user_id=user_id)