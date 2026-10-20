from typing import Literal

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

    # Document storage (app/integrations/storage). Australian regions only:
    # docs/child-document-retention-policy.md. GCS credentials come from
    # Application Default Credentials; S3's from the standard AWS chain.
    STORAGE_PROVIDER: Literal["gcs", "s3"] = "gcs"
    DOCUMENT_BUCKET: str
    S3_REGION: str = "ap-southeast-2"

    # Email (app/integrations/email, docs/email-policy.md). "log" writes
    # emails to the app log instead of sending (dev and tests); "ses" sends
    # through Amazon SES in Sydney.
    EMAIL_PROVIDER: Literal["log", "ses"] = "log"
    SES_REGION: str = "ap-southeast-2"
    SES_FROM_ADDRESS: str = "no-reply@jnb-digital.com.au"
    # Both without open/click tracking; the TLS one requires an encrypted
    # connection (password reset and kiosk PIN emails).
    SES_CONFIGURATION_SET: str | None = None
    SES_TLS_CONFIGURATION_SET: str | None = None
    # Send as the tenant's SES tenant (one per tenant). Off until the SES
    # tenants exist.
    SES_USE_TENANTS: bool = True
    # The SNS topic the configuration sets publish bounces, complaints and
    # deliveries to; the webhook only accepts messages from it.
    SES_EVENTS_TOPIC_ARN: str | None = None
    # Optional: values in .env don't reach boto3 on their own; in Cloud Run
    # they come from Secret Manager as environment variables.
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None

    # Links in emails: the tenant's site. {tenant} is the tenant code, e.g.
    # "http://{tenant}.localhost:5173" in dev. Defaults to
    # https://{tenant}.<BASE_DOMAIN>; a tenant's custom domain wins.
    FRONTEND_URL_TEMPLATE: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()