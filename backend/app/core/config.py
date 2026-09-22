from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "BusinessHub Backend"
    app_version: str = "0.1.0"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_reload: bool = True

    api_v1_prefix: str = "/api/v1"

    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    cors_allow_headers: List[str] = ["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"]

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10

    dev_seed_email: str = "dev@businesshub.dev"
    dev_seed_password: str = "DevSeedPass123!"
    dev_seed_name: str = "Development Owner"

    dev_seed_superadmin_email: str = "superadmin@businesshub.dev"
    dev_seed_superadmin_password: str = "SuperAdminPass123!"
    dev_seed_superadmin_name: str = "Platform Super Admin"

    database_url: str = ""

    upload_dir: str = "uploads"
    max_upload_size_mb: int = 5


settings = Settings()