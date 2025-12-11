from pydantic_settings import BaseSettings

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Seguridad y DB
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    DATABASE_URL: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"



settings = Settings()  # type: ignore
