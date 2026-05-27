from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    APP_NAME: str = 'Coworking AI Orchestrator'
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = 'postgresql+asyncpg://postgres:postgres@postgres:5432/coworking_ai'
    REDIS_URL: str = 'redis://localhost:6379/0'

    # AI Providers
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # Fireworks AI (Primary)
    FIREWORKS_API_KEY: Optional[str] = None
    FIREWORKS_BASE_URL: str = 'https://api.fireworks.ai/inference/v1'
    FIREWORKS_MODEL: str = 'accounts/fireworks/routers/kimi-k2p6-turbo'
    DEFAULT_LLM_MODEL: str = 'accounts/fireworks/routers/kimi-k2p6-turbo'

    # Upstream Services
    SEARCH_URL: str = 'http://localhost:8001'
    PRICING_URL: str = 'http://localhost:8002'
    ORCHESTRATOR_URL: str = 'http://localhost:8000'

    # Notifications
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None
    SMTP_FROM: str = 'visits@coworking-ai.com'
    WHATSAPP_ENABLED: bool = False

    # Security
    JWT_SECRET: str = 'dev-secret-change-in-production'
    JWT_ALGORITHM: str = 'HS256'

@lru_cache()
def get_settings() -> Settings:
    return Settings()
