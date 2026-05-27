from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "Coworking AI API Gateway"
    DEBUG: bool = False
    PORT: int = 8080
    
    # Auth
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # CORS
    CORS_ORIGINS: list = ["*"]
    
    # Upstream Services (localhost for direct PM2 deployment)
    ORCHESTRATOR_URL: str = "http://localhost:8000"
    SEARCH_URL: str = "http://localhost:8001"
    PRICING_URL: str = "http://localhost:8002"
    ANALYTICS_URL: str = "http://localhost:8003"
    NOTIFICATION_URL: str = "http://localhost:8004"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
