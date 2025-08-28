# import os
# from typing import Dict, List, Optional

# from fastapi import HTTPException, Body, Depends
# from github import Github, GithubException
# from pydantic import BaseModel, Field
# from dotenv import load_dotenv

# load_dotenv()

# GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
# GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY")

# g = Github(GITHUB_TOKEN)
# repo = g.get_repo(GITHUB_REPO)

# class TemplateValues(BaseModel):
#     NAMESPACE: str
#     NAME: str
#     PORT: int
#     HOST: str
#     IMAGE: str
#     REQUEST_MEMORY: str = "128Mi"
#     REQUEST_CPU: str = "100m"
#     LIMIT_MEMORY: str = "256Mi"
#     LIMIT_CPU: str = "200m"

# def get_github_client():
#     return Github(GITHUB_TOKEN)

# def get_repo(github_client: Github):
#     try:
#         return github_client.get_repo(GITHUB_REPO)
#     except GithubException as e:
#         raise HTTPException(status_code=404, detail=f"레포지토리를 찾을 수 없습니다: {str(e)}")

# def replace_template_values(template_content: str, values: Dict) -> str:
#     result = template_content
#     for key, value in values.items():
#         placeholder = f"{{{key}}}"
#         result = result.replace(placeholder, str(value))
#     return result