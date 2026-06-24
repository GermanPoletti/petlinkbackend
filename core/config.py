from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    DATABASE_URL: str

    GMAIL_USER: str = "petlinkproject@gmail.com"
    GMAIL_APP_PASSWORD: str = ""
    BASE_URL: str = "http://192.168.15.102:8000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()  # type: ignore
