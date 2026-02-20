from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseModel):
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME: str = os.getenv("DB_NAME", "notes_platform")
    MONGO_SERVER_SELECTION_TIMEOUT_MS: int = int(
        os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "1500")
    )

    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    JWT_COOKIE_NAME: str = os.getenv("JWT_COOKIE_NAME", "access_token")
    REFRESH_COOKIE_NAME: str = os.getenv("REFRESH_COOKIE_NAME", "refresh_token")
    JWT_COOKIE_SECURE: bool = os.getenv("JWT_COOKIE_SECURE", "false").lower() == "true"
    JWT_COOKIE_SAMESITE: str = os.getenv("JWT_COOKIE_SAMESITE", "lax")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    CACHE_DEFAULT_TTL_SECONDS: int = int(os.getenv("CACHE_DEFAULT_TTL_SECONDS", "60"))
    LOG_JSON: bool = os.getenv("LOG_JSON", "true").lower() == "true"
    SLOW_QUERY_THRESHOLD_MS: int = int(os.getenv("SLOW_QUERY_THRESHOLD_MS", "250"))
    AI_JOB_MAX_ATTEMPTS: int = int(os.getenv("AI_JOB_MAX_ATTEMPTS", "3"))
    ENABLE_SECURITY_HEADERS: bool = os.getenv("ENABLE_SECURITY_HEADERS", "true").lower() == "true"


def validate_settings(cfg: Settings):
    if not cfg.JWT_SECRET_KEY.strip():
        raise RuntimeError("JWT_SECRET_KEY must be set in the environment")


settings = Settings()
validate_settings(settings)
