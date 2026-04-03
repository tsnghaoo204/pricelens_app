from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str

    BEARER_TOKEN: str
    CAMPAIGN_ID: str
    API_KEY_SECRET: str

    class Config:
        env_file = ".env"

settings = Settings()
