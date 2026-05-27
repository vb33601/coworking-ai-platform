from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    APP_NAME: str = "Search Service"
    DEBUG: bool = False
    class Config:
        env_file = ".env"
