import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = os.getenv("APP_NAME")
    PROJECT_VERSION: str = os.getenv("APP_VERSION")
    CORS_ORIGINS: str = "*"
    DATABASE_URL: str = os.getenv("DATABASE_URL")

    class Config:
        extra = "allow"
        env_file = "../.env"
        case_sensitive = True


settings = Settings()