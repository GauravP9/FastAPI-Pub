from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",    # This is relative from where you are running the application
        env_file_encoding="utf-8"
    )   # Basically we are telling that we are going to check .env file for the secrets

    secret_key: SecretStr   # Special type wont leak this value in log/print statement
    algorithm: str = "HS256"   # standard algo for JWT
    access_token_expire_minutes: int = 30
# This variable mapped to env var and these are case insensetive

settings = Settings()   #Loaded everything from .env file

