from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # MongoDB
    MONGO_HOST: str
    MONGO_PORT: int
    MONGO_USER: str
    MONGO_PASSWORD: str
    MONGO_DATABASE: str

    # MySQL
    MYSQL_HOST: str
    MYSQL_PORT: int
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DATABASE: str

    # PostgreSQL
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DATABASE: str

    # AWS S3
    AWS_BUCKET_NAME: str
    AWS_REGION: Optional[str] = "us-east-1"

    # Docker Network (opcional)
    DOCKER_NETWORK: Optional[str] = "bridge"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()