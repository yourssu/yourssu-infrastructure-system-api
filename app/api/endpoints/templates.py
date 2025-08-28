from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from core.database import get_db
from core.enums import OrderBy
from schemas.applications import ApplicationResponse
from core.security import get_current_user_id, verify_token, verify_admin, oauth2_scheme
from crud.templates import crud_template
from schemas.templates import TemplateCreate, TemplateUpdate, TemplateResponse

router = APIRouter()

@router.post("/templates", response_model=TemplateResponse, status_code=201)
def create_template(
    *,
    db: Session = Depends(get_db),
    template_in: TemplateCreate,
    token: str = Depends(oauth2_scheme)
):
    """
    템플릿 생성하기
    """
    verify_token(token, db)
    user_id = get_current_user_id(token, db)
    
    # 템플릿 이름 중복 확인
    existing_template = crud_template.get_by_name(db, name=template_in.name)
    if existing_template:
        raise HTTPException(status_code=400, detail="이미 존재하는 템플릿 이름입니다.")
    
    try:
        template = crud_template.create(db, obj_in=template_in)
        return template
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create template: {str(e)}"
        )

@router.get("/templates", response_model=List[TemplateResponse])
def read_templates(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    order_by: OrderBy = OrderBy.CREATED_AT_DESC,
    token: str = Depends(oauth2_scheme)
):
    """
    템플릿 목록 조회
    """
    verify_token(token, db)
    return crud_template.get_multi(db, skip=skip, limit=limit, order_by=order_by)

@router.get("/templates/{template_id}", response_model=TemplateResponse)
def read_template(
    *,
    db: Session = Depends(get_db),
    template_id: int = Path(..., gt=0),
    token: str = Depends(oauth2_scheme)
):
    """
    템플릿 조회
    """
    verify_token(token, db)
    template = crud_template.get(db, id=template_id)
    if not template:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다.")
    return template

@router.put("/templates/{template_id}", response_model=TemplateResponse)
def update_template(
    *,
    db: Session = Depends(get_db),
    template_id: int = Path(..., gt=0),
    template_in: TemplateUpdate,
    token: str = Depends(oauth2_scheme)
):
    """
    템플릿 수정
    """
    verify_token(token, db)
    user_id = get_current_user_id(token, db)
    
    template = crud_template.get(db, id=template_id)
    if not template:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다.")
    
    if template.user_id != user_id:
        raise HTTPException(status_code=403, detail="템플릿을 수정할 권한이 없습니다.")
    
    try:
        template = crud_template.update(db, db_obj=template, obj_in=template_in)
        return template
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update template: {str(e)}"
        )

@router.delete("/templates/{template_id}", response_model=TemplateResponse)
def delete_template(
    *,
    db: Session = Depends(get_db),
    template_id: int = Path(..., gt=0),
    token: str = Depends(oauth2_scheme)
):
    """
    템플릿 삭제 (소프트 삭제)
    """
    verify_token(token, db)
    user_id = get_current_user_id(token, db)
    
    template = crud_template.get(db, id=template_id)
    if not template:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다.")
    
    if template.user_id != user_id:
        raise HTTPException(status_code=403, detail="템플릿을 삭제할 권한이 없습니다.")
    
    try:
        template = crud_template.remove(db, id=template_id)
        return template
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete template: {str(e)}"
        )