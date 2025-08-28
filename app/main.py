from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from api.endpoints import users, applications, deployments, auth, github, templates
from core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="유어슈 온프레미스 애플리케이션 및 배포 관리 API",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users")
app.include_router(applications.router, prefix=f"{settings.API_V1_STR}/applications")
app.include_router(deployments.router, prefix=f"{settings.API_V1_STR}/deployments")
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth")
# app.include_router(github.router, prefix=f"{settings.API_V1_STR}/github")
app.include_router(templates.router, prefix=f"{settings.API_V1_STR}/templates")

@app.get("/")
def root():
    return {"message": "유어슈 배포 관리 시스템 API에 오신 것을 환영합니다. /docs에서 API 문서를 확인하세요."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
    