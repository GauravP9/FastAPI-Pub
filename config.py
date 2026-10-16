from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(  # SettingsConfigDict - "Before validating settings, read variables from the .env file.
        env_file=".env",  # This is relative from where you are running the application
        env_file_encoding="utf-8",
    )  # Basically we are telling that we are going to check .env file for the secrets

    secret_key: SecretStr  # Special type wont leak this value in log/print statement
    algorithm: str = "HS256"  # standard algo for JWT
    access_token_expire_minutes: int = 30

    max_upload_size_bytes: int = 5 * 1024 * 1024  # 5MB - set this for image upload

    post_per_page:int = 10  # No of post/page
# These variables mapped to env var and these are case insensetive so system looks for these in .env file

settings = Settings()  # type: ignore # Loaded everything from .env file
