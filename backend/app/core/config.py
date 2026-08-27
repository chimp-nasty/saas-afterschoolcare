from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    APP_ENV: str = "dev"

    # Database
    DATABASE_URL: str

    # Frontend
    BASE_DOMAIN: str

    # Cookie settings
    COOKIE_NAME: str = "access_token"
    COOKIE_SECURE: bool = True
    COOKIE_HTTPONLY: bool = True
    COOKIE_SAMESITE: str = "none"
    COOKIE_PATH: str = "/"

    # JWT
    JWT_SECRET_KEY: str
    JWT_ISSUER: str = "my-api"
    JWT_AUDIENCE: str = "my-api-users"
    JWT_ALGORITHM: str = "HS256"
    JWT_CLOCK_SKEW_SECONDS: int = 30
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 90

    # Stripe
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str

    # Document storage
    DOCUMENT_BUCKET: str

    # AWS SES
    AWS_REGION: str

    SES_FROM_EMAIL: str
    SES_FROM_NAME: str
    SES_SUPPORT_EMAIL: str

    SES_TEMPLATE_PASSWORD_RESET: str
    SES_TEMPLATE_BOOKING_CONFIRMATION: str
    SES_TEMPLATE_REFUND_CONFIRMATION: str
    SES_TEMPLATE_ACCOUNT_REGISTRATION: str
    SES_TEMPLATE_MEDICAL_REVIEW_REQUIRED: str
    SES_TEMPLATE_MEDICAL_DOCUMENTS_REQUIRED: str
    SES_TEMPLATE_CHILD_APPROVED: str
    SES_TEMPLATE_CHILD_REJECTED: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()