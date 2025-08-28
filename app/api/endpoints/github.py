# import os
# from typing import Dict, List, Optional
# import yaml
# from fastapi import APIRouter, HTTPException, Body, Depends, Path
# from github import Github, GithubException
# from pydantic import BaseModel, Field
# import base64
# from sqlalchemy.orm import Session

# from core.database import get_db
# from core.security import get_current_user_id, verify_token, verify_admin, oauth2_scheme
# from core.github import get_github_client, get_repo, replace_template_values
# from crud.applications import crud_application
# from crud.templates import crud_template
# from schemas.templates import TemplateBase
# from services.github import get_github_file_names, get_github_file, get_all_github_files

# router = APIRouter()

# @router.get("/{app_id}", response_model=List[str])
# async def read_github_file_names(
#     *,
#     db: Session = Depends(get_db),
#     app_id: int = Path(..., gt=0),
#     token: str = Depends(oauth2_scheme),
#     github_client: Github = Depends(get_github_client)
# ):
#     """GitHub 레포지토리에서 애플리케이션의 모든 파일 이름 가져오기"""
#     verify_token(token, db)

#     application = crud_application.get(db, id=app_id)

#     return get_github_file_names(application_name=application.name, github_client=github_client)
    

# @router.get("/{app_id}/file", response_model=TemplateBase)
# async def read_github_file(
#     *,
#     db: Session = Depends(get_db),
#     app_id: int = Path(..., gt=0),
#     file_name: str,
#     token: str = Depends(oauth2_scheme),
#     github_client: Github = Depends(get_github_client)
# ):
#     """GitHub 레포지토리에서 애플리케이션의 특정 파일 내용 가져오기"""
#     verify_token(token, db)

#     application = crud_application.get(db, id=app_id)

#     return get_github_file(application_name=application.name, file_name=file_name, github_client=github_client)
    
# @router.get("/{app_id}/all", response_model=List[TemplateBase])
# async def read_all_github_files(
#     *,
#     db: Session = Depends(get_db),
#     app_id: int = Path(..., gt=0),
#     token: str = Depends(oauth2_scheme),
#     github_client: Github = Depends(get_github_client)
# ):
#     """GitHub 레포지토리에서 애플리케이션의 모든 파일과 내용 반환"""
#     verify_token(token, db)

#     application = crud_application.get(db, id=app_id)

#     return get_all_github_files(application_name=application.name, github_client=github_client)