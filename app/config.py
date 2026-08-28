from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables or .env file."""

    APP_NAME: str = "Embeddable Widget & Lead-Capture Platform"
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    DATABASE_URL: str = "sqlite:///./widget_platform.db"
    BASE_URL: str = "http://localhost:8000"

    # Rate limiting & payload size guard
    RATE_LIMIT_PER_MINUTE: int = 5
    MAX_PAYLOAD_SIZE_BYTES: int = 65536  # 64 KB limit

    # Testing & Provider fallback flags
    MOCK_GEO_PROVIDER_A_DOWN: bool = False
    MOCK_GEO_PROVIDER_B_DOWN: bool = False
    MOCK_EMAIL_SHOULD_FAIL: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Returns cached instance of the application settings."""
    return Settings()
