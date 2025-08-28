from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path, Query, BackgroundTasks, Body
from sqlalchemy.orm import Session
from github import Github
from datetime import datetime
import os
from dotenv import load_dotenv

from core.database import get_db
from core.security import oauth2_scheme, get_current_user_id, verify_token, verify_admin
from core.enums import DeploymentState, UserRole, OrderBy
from core.email import send_email, EmailSchema
from core.k8s import kubeconfig
from crud.deployments import crud_deployment
from crud.applications import crud_application
from crud.users import crud_user
from schemas.deployments import DeploymentCreate, DeploymentCreateWithManifests, DeploymentUpdateWithManifests, DeploymentApprove, DeploymentResponse, DeploymentImageUpdate, DeploymentPageResponse
from schemas.manifests import ManifestBase
from crud.manifests import crud_manifest
from services.kubernetes import KubernetesService

load_dotenv()

router = APIRouter()
kubernetes_service = KubernetesService()

@router.post("/", response_model=DeploymentResponse, status_code=201)
def request_deployment(
    *,
    db: Session = Depends(get_db),
    deployment_in: DeploymentCreateWithManifests,
    token: str = Depends(oauth2_scheme),
    background_tasks: BackgroundTasks
):
    """
    배포 요청
    - 링크에 {id}가 포함된 경우, 실제 deployment ID로 치환됩니다.
    - 이미 진행 중인 배포 요청(REQUEST 또는 RETURN 상태)이 있는 경우 새로운 요청을 생성할 수 없습니다.
    """
    verify_token(token, db)
    user_id = get_current_user_id(token, db)
    application = crud_application.get(db, id=deployment_in.deployment.application_id)
    if not application:
        raise HTTPException(status_code=404, detail="애플리케이션을 찾을 수 없습니다.")
    
    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    # if application.name not in user.accesses:
    #     raise HTTPException(status_code=401, detail=f"{application.name} 애플리케이션의 배포를 요청할 권한이 없습니다.")

    # 진행 중인 배포 요청 확인
    existing_deployments = crud_deployment.get_by_application(db, application_id=application.id)
    for deployment in existing_deployments:
        if deployment.state in [DeploymentState.REQUEST, DeploymentState.RETURN]:
            raise HTTPException(
                status_code=400,
                detail=f"이미 진행 중인 배포 요청이 있습니다. (ID: {deployment.id}, 상태: {deployment.state.value})"
            )

    try:
        deployment = crud_deployment.create(db, obj_in=deployment_in.deployment, user_id=user_id)

        for manifest in deployment_in.manifests:
            crud_manifest.create(db, obj_in=manifest, deployment_id=deployment.id)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create deployment: {str(e)}"
        )

    # Replace {id} in the link with actual deployment ID
    deployment_link = deployment_in.link.replace("{id}", str(deployment.id))

    admins = crud_user.get_by_role(db, role=UserRole.ADMIN)
    admin_emails = [admin.email for admin in admins]

    for email in admin_emails:
        email_data = EmailSchema(
            email_to=email,
            subject=f"[{application.name}] 새로운 배포 요청이 생성되었습니다.",
            body=f"[{application.user.part.value}/{application.user.nickname}] {application.name}의 배포 요청입니다. 다음 링크에서 확인할 수 있습니다.\n\n- 요청 메시지: {deployment.message}\n- 링크: {deployment_link}"
        )
        background_tasks.add_task(send_email, email_data)

    return deployment

@router.put("/{deployment_id}", response_model=DeploymentResponse)
def update_deployment(
    *,
    db: Session = Depends(get_db),
    deployment_id: int = Path(..., gt=0),
    deployment_in: DeploymentUpdateWithManifests,
    token: str = Depends(oauth2_scheme),
    background_tasks: BackgroundTasks
):
    """
    배포 요청 수정
    - is_request가 True인 경우: 요청 상태로 변경되고 관리자에게 이메일이 전송됩니다.
    - is_request가 False인 경우: 관리자만 수정할 수 있으며, 상태 변경 없이 수정만 진행됩니다.
    """
    verify_token(token, db)

    try:
        deployment = crud_deployment.get(db, id=deployment_id)
        if not deployment:
            raise HTTPException(status_code=404, detail="배포 요청을 찾을 수 없습니다.")
        
        if not deployment_in.is_request:
            # 관리자 권한 확인
            verify_admin(token, db)
        
        deployment = crud_deployment.update(db, db_obj=deployment, obj_in=deployment_in.deployment)

        if deployment_in.manifests:
            for manifest in deployment.manifests:
                crud_manifest.remove(db, id=manifest.id)

            for manifest in deployment_in.manifests:
                crud_manifest.create(db, obj_in=manifest, deployment_id=deployment.id)

        # is_request가 True인 경우 상태 변경 및 이메일 전송
        if deployment_in.is_request:
            deployment = crud_deployment.update_state(
                db=db,
                id=deployment_id,
                admin_id=None,
                state=DeploymentState.REQUEST,
                comment=None
            )

            # 관리자들에게 이메일 전송
            admins = crud_user.get_by_role(db, role=UserRole.ADMIN)
            admin_emails = [admin.email for admin in admins]

            deployment_link = deployment_in.link.replace("{id}", str(deployment.id))

            for email in admin_emails:
                email_data = EmailSchema(
                    email_to=email,
                    subject=f"[{deployment.application.name}] 배포 요청이 수정되었습니다.",
                    body=f"[{deployment.user.part.value}/{deployment.user.nickname}] {deployment.application.name}의 배포 요청이 수정되었습니다. 다음 링크에서 확인할 수 있습니다.\n\n- 요청 메시지: {deployment.message}\n- 링크: {deployment_link}"
                )
                background_tasks.add_task(send_email, email_data)

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update deployment: {str(e)}"
        )

    return deployment

@router.get("/", response_model=DeploymentPageResponse)
def read_deployments(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    order_by: OrderBy = OrderBy.CREATED_AT_DESC,
    token: str = Depends(oauth2_scheme)
):
    """
    배포 목록 조회
    """
    verify_token(token, db)
    
    deployments = crud_deployment.get_multi(db, skip=skip, limit=limit, order_by=order_by)
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

@router.get("/state", response_model=DeploymentPageResponse)
def read_deployment_by_state(
    *,
    db: Session = Depends(get_db),
    state: DeploymentState,
    skip: int = 0,
    limit: int = 100,
    order_by: OrderBy = OrderBy.CREATED_AT_DESC,
    token: str = Depends(oauth2_scheme)
):
    """
    요청 상태로 배포 전체 조회
    """
    verify_token(token, db)
    deployments = crud_deployment.get_by_state(db, state=state, skip=skip, limit=limit, order_by=order_by)
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

@router.get("/{deployment_id}", response_model=DeploymentResponse)
def read_deployment(
    *,
    db: Session = Depends(get_db),
    deployment_id: int = Path(..., gt=0),
    token: str = Depends(oauth2_scheme)
):
    """
    배포 조회
    """
    verify_token(token, db)
    deployment = crud_deployment.get(db, id=deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="배포 요청을 찾을 수 없습니다.")
    return deployment

@router.patch("/{deployment_id}", response_model=DeploymentResponse)
def update_state(
    *,
    db: Session = Depends(get_db),
    deployment_id: int = Path(..., gt=0),
    deployment_in: DeploymentApprove,
    token: str = Depends(oauth2_scheme),
    background_tasks: BackgroundTasks,
    # github_client: Github = Depends(get_github_client)
):
    """
    배포 요청 상태 업데이트
    """
    verify_token(token, db)
    verify_admin(token, db)

    user_id = get_current_user_id(token, db)
    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    deployment = crud_deployment.get(db, id=deployment_id)
    
    if deployment_in.state == DeploymentState.APPROVAL:
        manifests = []
        for manifest in deployment.manifests:
            manifests.append(ManifestBase(file_name=manifest.file_name, content=manifest.content))
        
        kubernetes_service.apply_k8s(manifests=manifests)

        # 배포 완료되면 승인 상태로 업데이트
        try:
            applied_deployment = crud_deployment.get_applied(db, application_id=deployment.application_id)
            if applied_deployment:
                crud_deployment.update_applied(db, id=applied_deployment.id, is_applied=False)
            crud_deployment.update_state(db, id=deployment_id, admin_id=user_id, state=deployment_in.state, comment=deployment_in.comment)
            crud_application.approve(db, id=deployment.application.id)
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update deployment: {str(e)}"
            )
    else:
        crud_deployment.update_state(db, id=deployment_id, admin_id=user_id, state=deployment_in.state, comment=deployment_in.comment)

    deployment_link = deployment_in.link.replace("{id}", str(deployment.id))

    email_data = EmailSchema(
        email_to=deployment.user.email,
        subject=f"[{deployment.application.name}] 배포 요청이 평가되었습니다.",
        body=f"{deployment.application.name}의 배포 요청이 평가되었습니다.\n\n- 평가 상태: {deployment.state.value}\n- 응답 메시지: [{user.part.value}/{user.nickname}]{deployment.comment}\n- 링크: {deployment_link}"
    )
    background_tasks.add_task(send_email, email_data)

    return deployment

@router.post("/update-image", response_model=DeploymentResponse)
def update_deployment_image(
    *,
    db: Session = Depends(get_db),
    update_in: DeploymentImageUpdate,
    token: str = Depends(oauth2_scheme)
):
    """
    GitHub Actions에서 호출하는 이미지 업데이트 API.
    새 이미지로 deployment를 생성하고 즉시 적용합니다.
    """
    if token != os.getenv("API_TOKEN"):
        raise HTTPException(status_code=401, detail="Unauthorized Github Actions User")
    
    # 현재 배포된 deployment
    latest_deployment = crud_deployment.get_applied(db, application_id=update_in.application_id)
    
    if not latest_deployment:
        raise HTTPException(
            status_code=404,
            detail="No previous deployment found for this application"
        )

    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # manifest 생성 및 클러스터에 적용
        new_manifests = kubernetes_service.apply_deployment_update(
            deployment=latest_deployment,
            new_image_url=update_in.image_url
        )

        # 새로운 deployment 생성 (자동 승인 상태로)
        new_deployment = DeploymentCreate(
            application_id=update_in.application_id,
            domain_name=latest_deployment.domain_name,
            cpu_requests=latest_deployment.cpu_requests,
            memory_requests=latest_deployment.memory_requests,
            cpu_limits=latest_deployment.cpu_limits,
            memory_limits=latest_deployment.memory_limits,
            port=latest_deployment.port,
            image_url=update_in.image_url,
            replicas=latest_deployment.replicas,
            message=f"CI/CD automated deployment (commit: {update_in.commit_sha})"
        )

        # Deployment 생성 및 자동 승인 상태로 설정
        deployment = crud_deployment.create(
            db=db, 
            obj_in=new_deployment,
            user_id=get_current_user_id(token, db)
        )

        # 즉시 승인 상태로 업데이트        
        applied_deployment = crud_deployment.get_applied(db, application_id=deployment.application_id)
        if applied_deployment:
            crud_deployment.update_applied(db, id=applied_deployment.id, is_applied=False)

        deployment = crud_deployment.update_state(
            db=db,
            id=deployment.id,
            admin_id=get_current_user_id(token, db),  # CI/CD 봇이 승인자가 됨
            state=DeploymentState.APPROVAL,
            comment=f"Automatically approved by CI/CD (commit: {update_in.commit_sha})"
        )

        # 생성된 manifest DB에 저장
        for manifest in new_manifests:
            crud_manifest.create(
                db=db,
                obj_in=manifest,
                deployment_id=deployment.id
            )

        db.commit()
        return deployment

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update deployment: {str(e)}"
        )
    
@router.post("/{deployment_id}/rollback", response_model=DeploymentResponse)
def rollback_deployment(
    *,
    db: Session = Depends(get_db),
    deployment_id: int = Path(..., gt=0),
    token: str = Depends(oauth2_scheme)
):
    """
    배포 롤백
    """
    verify_token(token, db)

    try:
        previous_deployment = crud_deployment.get(db, id=deployment_id)
        current_deployment = crud_deployment.get_applied(db, application_id=previous_deployment.application_id)
        
        if not previous_deployment:
            raise HTTPException(status_code=404, detail="이전 배포를 찾을 수 없습니다.")
        
        if not current_deployment:
            raise HTTPException(status_code=404, detail="현재 배포를 찾을 수 없습니다.")
        
        if previous_deployment.state != DeploymentState.APPROVAL:
            raise HTTPException(status_code=400, detail="승인된 배포만 롤백할 수 있습니다.")
        
        manifests = []
        for manifest in previous_deployment.manifests:
            manifests.append(ManifestBase(file_name=manifest.file_name, content=manifest.content))

        kubernetes_service.apply_k8s(manifests=manifests)

        crud_deployment.update_applied(db, id=current_deployment.id, is_applied=False)
        crud_deployment.update_applied(db, id=previous_deployment.id, is_applied=True)

        db.commit()
        return previous_deployment
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to rollback deployment: {str(e)}"
        )