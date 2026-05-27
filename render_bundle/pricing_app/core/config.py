from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    APP_NAME: str = "Pricing Service"
    DEBUG: bool = False
    class Config:
        env_file = ".env"
