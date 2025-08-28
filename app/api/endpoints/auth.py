from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Form, Path, status
from sqlalchemy.orm import Session

from core.database import get_db
from crud.users import crud_user
from core.security import (
    get_password_hash, verify_password, create_access_token,
    create_refresh_token, oauth2_scheme, verify_admin, verify_token,
    ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
)
from schemas.users import UserCreate, UserResponse
from schemas.auth import Token
from core.enums import UserPart
from models.models import RefreshToken
import random

router = APIRouter()

@router.post("/login", response_model=Token, status_code=201)
def login(
    *, 
    db: Session = Depends(get_db), 
    username: str = Form(...), 
    password: str = Form(...)
):
    """
    로그인
    """
    user = crud_user.get_by_email(db, email=username)
    if not user:
        raise HTTPException(
            status_code=400,
            detail="등록되지 않은 이메일입니다."
        )

    if not verify_password(password, user.password):
        raise HTTPException(
            status_code=400,
            detail="비밀번호가 틀렸습니다."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="활성화되지 않은 사용자입니다. 관리자에게 문의 바랍니다."
        )

    # 기존 리프레시 토큰 삭제
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
    
    # 새로운 리프레시 토큰 생성
    refresh_token = create_refresh_token()
    refresh_token_expires = datetime.now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    db_refresh_token = RefreshToken(
        token=refresh_token,
        user_id=user.id,
        expires_at=refresh_token_expires
    )
    db.add(db_refresh_token)
    db.commit()

    access_token = create_access_token(
        data={"id": str(user.id), "role": user.role}
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )

@router.post("/refresh", response_model=Token)
def refresh_token(
    *,
    db: Session = Depends(get_db),
    refresh_token: str = Form(...)
):
    """
    액세스 토큰 갱신
    """
    db_refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_token,
        RefreshToken.expires_at > datetime.utcnow()
    ).first()
    
    if not db_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    user = crud_user.get(db, id=db_refresh_token.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # 새로운 액세스 토큰 생성
    access_token = create_access_token(
        data={"id": str(user.id), "role": user.role}
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )

@router.post("/", response_model=UserResponse, status_code=201)
def create_user(*, db: Session = Depends(get_db), user_in: UserCreate):
    """
    회원가입(사용자 생성)
    """
    if not user_in.email.endswith("urssu@gmail.com"):
        raise HTTPException(
            status_code=400,
            detail="유어슈 Gmail을 사용해주세요."
        )

    user = crud_user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="이미 등록된 이메일입니다."
        )

    db_obj = UserCreate(
        email=user_in.email,
        nickname=user_in.nickname,
        part=user_in.part,
        password=get_password_hash(user_in.password),
        avatar_id=random.randint(1, 12)
    )

    return crud_user.create(db, obj_in=db_obj)

@router.post("/{user_id}/activate", response_model=UserResponse, status_code=201)
def activate_user(
    *, 
    db: Session = Depends(get_db), 
    user_id: int = Path(..., gt=0),
    token: str = Depends(oauth2_scheme)
):
    """
    사용자 활성화
    """
    verify_token(token, db)
    verify_admin(token, db)
    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=400,
            detail="사용자를 찾을 수 없습니다."
        )
    
    return crud_user.activate(db, user=user)

@router.get("/parts", response_model=list[str])
def get_user_parts():
    """
    사용자 파트 목록 조회
    """
    return [part.value for part in UserPart]

@router.get("/me", response_model=UserResponse)
def get_current_user(
    *,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """
    현재 사용자 정보 조회
    """
    user = verify_token(token, db)
    return user