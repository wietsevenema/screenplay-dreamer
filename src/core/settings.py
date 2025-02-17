from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""

    PROJECT_ID: str = Field(..., description="Google Cloud Project ID")
    GEMINI_REGION: str = Field(
        "us-central1", description="Google Cloud Region to use for the Gemini API"
    )
    BUCKET_NAME: str = Field(..., description="Google Cloud Storage bucket name")
    GOOGLE_CLIENT_ID: str = Field(
        ...,
        description="Google OAuth client ID",
    )
    JWT_SECRET: str = Field(..., description="Secret key for JWT tokens")
    JWT_ALGORITHM: str = Field("HS256", description="Algorithm for JWT tokens")
    TOKEN_EXPIRE_DAYS: int = Field(30, description="JWT token expiration in days")
    CREATIVE_MODEL: str = Field(
        "gemini-2.0-pro-exp-02-05",
        description="Model to use for creative generation tasks",
    )
    FLASH_MODEL: str = Field(
        "gemini-2.0-flash-001",
        description="Model to use for fast, structured generation tasks",
    )

    class Config:
        env_file = ".env"


settings = Settings()
