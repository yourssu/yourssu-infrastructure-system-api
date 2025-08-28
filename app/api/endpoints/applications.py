from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session
import re

from core.database import get_db
from core.security import get_current_user_id, verify_token, verify_admin, oauth2_scheme
from core.enums import OrderBy, UserRole
from crud.users import crud_user
from crud.applications import crud_application
from crud.deployments import crud_deployment
from crud.manifests import crud_manifest
from schemas.applications import *
from schemas.deployment_status import DeploymentStatus, DeploymentStatusPage
from schemas.deployments import DeploymentResponse, DeploymentPageResponse
from schemas.manifests import ManifestBase
from services.kubernetes import KubernetesService

router = APIRouter()
kubernetes_service = KubernetesService()

def validate_application_name(name: str) -> None:
    """
    애플리케이션 이름이 영어 소문자와 하이픈(-)의 조합으로만 이루어져 있는지 검증합니다.
    """
    if not re.match(r'^[a-z][a-z0-9-]*$', name):
        raise HTTPException(
            status_code=400,
            detail="애플리케이션 이름은 영어 소문자로 시작하고, 영어 소문자, 숫자, 하이픈(-)만 사용할 수 있습니다."
        )

@router.post("/", response_model=ApplicationResponse, status_code=201)
def request_application(
    *,
    db: Session = Depends(get_db),
    app_in: ApplicationCreate,
    token: str = Depends(oauth2_scheme)
):
    """
    애플리케이션 생성하기. 생성 후 이름은 변경할 수 없습니다.
    - 이름은 영어 소문자로 시작하고, 영어 소문자, 숫자, 하이픈(-)만 사용할 수 있습니다.
    """
    verify_token(token, db)
    validate_application_name(app_in.name)
    
    user_id = get_current_user_id(token, db)
    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    # 애플리케이션 이름 중복 확인
    existing_app = crud_application.get_by_name(db, name=app_in.name)
    if existing_app:
        raise HTTPException(status_code=400, detail="이미 존재하는 애플리케이션 이름입니다.")
    
    application = crud_application.create(db, obj_in=app_in, user_id=user_id)
    # crud_user.add_user_access(db, user=user, access_to_add=application.name)

    return application

@router.get("/", response_model=ApplicationResponses)
def read_applications(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    order_by: OrderBy = OrderBy.CREATED_AT_DESC,
    token: str = Depends(oauth2_scheme)
):
    """
    애플리케이션 목록 조회
    """
    verify_token(token, db)
    applications = crud_application.get_multi(db, skip=skip, limit=limit, order_by=order_by)
    total_count = crud_application.get_count(db)
    total_pages = (total_count + limit - 1) // limit if limit > 0 else 0

    deployment_state_count = {
        "request_count": 0,
        "check_count": 0,
        "return_count": 0,
        "approval_count": 0,
    }

    application_list = []
    for application in applications:
        for deployment in application.deployments:
            if deployment.state == "REQUEST":
                deployment_state_count["request_count"] += 1
            elif deployment.state == "CHECK":
                deployment_state_count["check_count"] += 1
            elif deployment.state == "RETURN":
                deployment_state_count["return_count"] += 1
            elif deployment.state == "APPROVAL":
                deployment_state_count["approval_count"] += 1

        application_list.append(
            ApplicationResponse(
                id=application.id,
                name=application.name,
                description=application.description,
                user=application.user,
                is_approved=application.is_approved,
                created_at=application.created_at,
                updated_at=application.updated_at,
                deleted_at=application.deleted_at,
            )
        )

    return ApplicationResponses(
        data=application_list,
        state_count=DeploymentStateCount(**deployment_state_count),
        current_limit=limit,
        current_skip=skip,
        total_count=total_count,
        total_pages=total_pages
    )


@router.get("/{app_id}", response_model=ApplicationResponse)
def read_application(
    *,
    db: Session = Depends(get_db),
    app_id: int = Path(..., gt=0),
    token: str = Depends(oauth2_scheme)
):
    """
    애플리케이션 조회
    """
    verify_token(token, db)
    application = crud_application.get(db, id=app_id)
    if not application:
        raise HTTPException(status_code=404, detail="애플리케이션을 찾을 수 없습니다.")

    return application

@router.put("/{app_id}", response_model=ApplicationResponse)
def update_application(
    *,
    db: Session = Depends(get_db),
    app_id: int = Path(..., gt=0),
    app_in: ApplicationUpdate,
    token: str = Depends(oauth2_scheme)
):
    """
    애플리케이션 설명 수정
    """
    verify_token(token, db)

    application = crud_application.get(db, id=app_id)
    if not application:
        raise HTTPException(status_code=404, detail="애플리케이션을 찾을 수 없습니다.")
    
    return crud_application.update(db, db_obj=application, obj_in=app_in)

@router.delete("/{app_id}", response_model=ApplicationResponse)
def delete_application(
    *,
    db: Session = Depends(get_db),
    app_id: int = Path(..., gt=0),
    token: str = Depends(oauth2_scheme)
):
    """
    애플리케이션 삭제 (소프트 삭제)
    """
    verify_token(token, db)
    verify_admin(token, db)
    application = crud_application.get(db, id=app_id)
    if not application:
        raise HTTPException(status_code=404, detail="애플리케이션을 찾을 수 없습니다.")
    
    user_id = get_current_user_id(token, db)
    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    if application.user_id != user_id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=401, detail=f"{application.name} 애플리케이션을 삭제할 권한이 없습니다.")
    
    try:
        deployments = crud_deployment.get_by_application(db, application_id=app_id)
        
        for deployment in deployments:
            manifests = crud_manifest.get_by_deployment(db, deployment_id=deployment.id)

            kubernetes_service.delete_k8s(manifests=manifests)
            
            for manifest in manifests:
                crud_manifest.remove(db, id=manifest.id)
            
            # Soft delete the deployment
            crud_deployment.remove(db, id=deployment.id)
        
        application = crud_application.remove(db, id=app_id)
        # crud_user.remove_user_access(db, user=application.user, access_to_remove=application.name)
        return application
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"애플리케이션을 삭제 중 오류가 발생했습니다.: {str(e)}"
        )

@router.get("/{app_id}/deployments", response_model=DeploymentPageResponse)
def read_application_deployments(
    *,
    db: Session = Depends(get_db),
    app_id: int = Path(..., gt=0),
    skip: int = 0,
    limit: int = 100,
    order_by: OrderBy = OrderBy.CREATED_AT_DESC,
    token: str = Depends(oauth2_scheme)
):
    """
    애플리케이션의 배포 목록 조회
    """
    verify_token(token, db)
    application = crud_application.get(db, id=app_id)
    if not application:
        raise HTTPException(status_code=404, detail="애플리케이션을 찾을 수 없습니다.")
    
    deployments = crud_deployment.get_by_application(db, application_id=app_id, skip=skip, limit=limit, order_by=order_by)
    total_count = crud_deployment.get_count(db)
    total_pages = (total_count + limit - 1) // limit if limit > 0 else 0

    # ORM 모델을 Pydantic 모델로 변환
    deployment_responses = []
    for deployment in deployments:
        # 매니페스트 객체들을 ManifestBase 형식으로 변환
        manifest_list = []
        if deployment.manifests:
            for manifest in deployment.manifests:
                manifest_list.append(
                    ManifestBase(
                        file_name=manifest.file_name,
                        content=manifest.content
                    )
                )
        
        # 각 deployment 항목을 DeploymentResponse로 변환
        deployment_dict = {
            # DeploymentBase 필드
            "domain_name": deployment.domain_name,
            "cpu_requests": deployment.cpu_requests,
            "memory_requests": deployment.memory_requests,
            "cpu_limits": deployment.cpu_limits,
            "memory_limits": deployment.memory_limits,
            "port": deployment.port,
            "image_url": deployment.image_url,
            "replicas": deployment.replicas,
            "message": deployment.message,
            
            # DeploymentResponse 추가 필드
            "id": deployment.id,
            "application_id": deployment.application_id,
            "comment": deployment.comment,
            "is_applied": deployment.is_applied,
            "state": deployment.state,
            "user_id": deployment.user_id,
            "admin_id": deployment.admin_id,
            "manifests": manifest_list,
            "created_at": deployment.created_at,
            "updated_at": deployment.updated_at,
            "deleted_at": deployment.deleted_at,
        }
        
        deployment_responses.append(DeploymentResponse(**deployment_dict))

    return DeploymentPageResponse(
        data=deployment_responses,
        current_limit=limit,
        current_skip=skip,
        total_count=total_count,
        total_pages=total_pages
    )

@router.get("/cluster/status", response_model=DeploymentStatusPage)
def get_all_status(
    *,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    order_by: OrderBy = OrderBy.CREATED_AT_DESC,
    token: str = Depends(oauth2_scheme)
):
    """애플리케이션의 모든 배포 상태를 조회합니다."""
    applications = crud_application.get_multi(db, skip=skip, limit=limit, order_by=order_by)
    deployment_status = kubernetes_service.get_all_applications_status(applications=applications)
    total_count = crud_application.get_count(db)
    total_pages = (total_count + limit - 1) // limit if limit > 0 else 0

    return DeploymentStatusPage(
        data=deployment_status,
        current_limit=limit,
        current_skip=skip,
        total_count=total_count,
        total_pages=total_pages
    )

@router.get("/{app_id}/cluster/status", response_model=DeploymentStatus)
def get_status(
    *,
    db: Session = Depends(get_db),
    app_id: int = Path(..., gt=0),
    token: str = Depends(oauth2_scheme)
):
    """특정 애플리케이션의 배포 상태를 조회합니다."""
    application = crud_application.get(db, id=app_id)
    if not application:
        raise HTTPException(status_code=404, detail="배포 요청을 찾을 수 없습니다.")
    return kubernetes_service.get_application_status(
            application_id=application.id,
            deployment_name=application.name,
            namespace=application.name
        )

@router.post("/unique", response_model=ApplicationUniqueResponse)
def check_application_name(
    *,
    db: Session = Depends(get_db),
    request: ApplicationUniqueRequest,
    token: str = Depends(oauth2_scheme)
):
    """
    애플리케이션 이름 unique 조회
    - 이름은 영어 소문자로 시작하고, 영어 소문자, 숫자, 하이픈(-)만 사용할 수 있습니다.
    """
    verify_token(token, db)
    validate_application_name(request.name)
    
    application = crud_application.get_by_name(db, request.name)
    if not application:
        response = ApplicationUniqueResponse(is_unique=True)
    else:
        response = ApplicationUniqueResponse(is_unique=False)

    return response