from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):  # These variables mapped to env var and these are case insensetive so system looks for these in .env file
    model_config = SettingsConfigDict(  # SettingsConfigDict - "Before validating settings, read variables from the .env file.
        env_file=".env",  # This is relative from where you are running the application
        env_file_encoding="utf-8",
    )  # Basically we are telling that we are going to check .env file for the secrets

    # DATABASE URL
    database_url:str    # No default value so this needs to be setup in .env file or in system directly as str

    # HASHING CONFIG
    secret_key: SecretStr  # Special type wont leak this value in log/print statement
    algorithm: str = "HS256"  # standard algo for JWT
    access_token_expire_minutes: int = 30

    # IMG SIZE - PILLOW
    max_upload_size_bytes: int = 5 * 1024 * 1024  # 5MB - set this for image upload

    # PAGINATION
    post_per_page: int = 10  # No of post/page

    reset_token_expire_minutes: int = 60  # Token expire for reset feature

    # MAIL SETTINGS 
    mail_server: str = "localhost"
    mail_port: int = 587
    mail_username: str = ""
    mail_password: SecretStr = SecretStr("")
    mail_from: str = "FastAPI Blog <info.fastapi@resend.dev>"
    mail_use_tls: bool = True

    frontend_url: str = "http://localhost:8000"  # Userd for attacker may trick us into sending reset email with links to redirect to their site [DuplicateSite Attacks]

    
settings = Settings()  # type: ignore # Loaded everything from .env file
