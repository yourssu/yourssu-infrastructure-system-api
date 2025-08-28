from typing import List
from fastapi import HTTPException
from github import Github, GithubException
import base64
from sqlalchemy.orm import Session

from core.github import get_repo, replace_template_values
from crud.applications import crud_application
from crud.templates import crud_template
from schemas.manifests import ManifestBase
from schemas.templates import TemplateBase

def get_all_templates(db: Session, skip: int = 0, limit: int = 100) -> List[TemplateBase]:
    """모든 템플릿 파일과 내용을 가져옴"""
    return crud_template.get_multi(db, skip=skip, limit=limit)

def get_github_file_names(
    application_name: str,
    github_client: Github,
) -> List[str]:
    """GitHub 레포지토리에서 모든 파일 이름 가져오기"""
    repo = get_repo(github_client)
    
    try:
        contents = repo.get_contents(application_name)
        return [content.name for content in contents if content.type == "file"]
    except GithubException as e:
        if e.status == 404:
            return []
        raise HTTPException(status_code=500, detail=f"GitHub API 에러: {str(e)}")
    
def get_github_file(
    application_name: str,
    file_name: str,
    github_client: Github,
) -> TemplateBase:
    """GitHub 레포지토리에서 특정 파일 내용 가져오기"""
    repo = get_repo(github_client)
    
    try:
        file_path = f"{application_name}/{file_name}"
        content = repo.get_contents(file_path)
        decoded_content = base64.b64decode(content.content).decode('utf-8')
        return TemplateBase(file_name=file_name, content=decoded_content)
    except GithubException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {application_name}/{file_name}")
        raise HTTPException(status_code=500, detail=f"GitHub API 에러: {str(e)}")

def get_all_github_files(
    application_name: str,
    github_client: Github,
) -> List[TemplateBase]:
    """GitHub 레포지토리의 모든 파일과 내용 반환"""
    repo = get_repo(github_client)
    
    try:
        contents = repo.get_contents(application_name)
        templates = []
        
        for content in contents:
            if content.type == "file" and content.name != ".gitkeep":
                decoded_content = base64.b64decode(content.content).decode('utf-8')
                templates.append(TemplateBase(file_name=content.name, content=decoded_content))
        
        return templates
    except GithubException as e:
        if e.status == 404:
            return {}
        raise HTTPException(status_code=500, detail=f"GitHub API 에러: {str(e)}")

def recreate_all_github_templates(
    application_name: str,
    manifests: List[ManifestBase],
    github_client: Github,
) -> None:
    """모든 GitHub 레포지토리에서 애플리케이션의 모든 파일 다시 생성"""
    repo = get_repo(github_client)
    
    clear_github_templates_directory(github_client)
    
    for file_name, content in manifests:
        file_path = f"{application_name}/{file_name}"
        repo.create_file(
            path=file_path,
            message=f"Create {file_name} with values",
            content=content
        )

def clear_github_templates_directory(
    application_name: str,
    github_client: Github,
) -> None:
    """GitHub 레포지토리의 애플리케이션 디렉토리 내 모든 파일 삭제"""
    repo = get_repo(github_client)
    
    try:
        # 디렉토리 내 모든 파일 가져오기
        contents = repo.get_contents(application_name)
        
        # 각 파일 삭제
        deleted_files = []
        for content in contents:
            if content.type == "file":
                repo.delete_file(
                    path=content.path,
                    message=f"Delete {content.name}",
                    sha=content.sha
                )
                deleted_files.append(content.name)
        
        # .gitkeep 파일 생성하여 빈 디렉토리 유지
        try:
            repo.create_file(
                path="application_name/.gitkeep",
                message="Create .gitkeep to maintain directory",
                content=""
            )
        except GithubException:
            # 이미 존재할 경우 무시
            pass
    except GithubException as e:
        if e.status == 404:
            # 디렉토리가 없으면 생성
            repo.create_file(
                path=f"{application_name}/.gitkeep",
                message=f"Create {application_name} directory",
                content=""
            )
        raise HTTPException(status_code=500, detail=f"GitHub API 에러: {str(e)}")