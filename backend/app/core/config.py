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
    # Lax: the API is on the same site as the pages (under /api), and
    # cookies have no Domain, so each belongs to one tenant's site.
    COOKIE_SAMESITE: str = "lax"
    COOKIE_PATH: str = "/"

    # JWT
    JWT_SECRET_KEY: str
    JWT_ISSUER: str = "my-api"
    JWT_AUDIENCE: str = "my-api-users"
    JWT_ALGORITHM: str = "HS256"
    JWT_CLOCK_SKEW_SECONDS: int = 30
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 90

    # Stripe. The platform's own keys; each tenant's payments go to its
    # connected account (Stripe Connect, tenancy.tenant_stripe_accounts).
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    # The Connect webhook endpoint's signing secret: events on connected
    # accounts (their checkouts and refunds, account updates). Empty
    # rejects every Connect event.
    STRIPE_CONNECT_WEBHOOK_SECRET: str = ""
    # Dev only: a test-mode connected account the dev seed links to
    # tenant1, so a rebuild doesn't need onboarding again.
    STRIPE_DEV_ACCOUNT_ID: str | None = None
    # "Connect with Stripe" (OAuth, linking a business's existing account):
    # the platform's client id (ca_...) from Settings > Connect > Onboarding
    # options > OAuth. Unset hides the option.
    STRIPE_CONNECT_CLIENT_ID: str | None = None

    # The platform's own site (not a tenant's), where the API also answers
    # under /api. Stripe's OAuth returns to
    # {API_BASE_URL}/api/stripe-account/v1/oauth/callback, which must be
    # listed as a redirect URI in Stripe's OAuth settings.
    API_BASE_URL: str = "http://localhost:8000"

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

    # Custom domains (docs/tenant-administration.md, section 7;
    # app/integrations/domains). "local" (dev): nothing is asked of Google
    # and every DNS record is found, so a domain goes live on its first
    # check. "google" when deployed: Certificate Manager, the load balancer
    # and public DNS.
    DOMAINS_PROVIDER: Literal["local", "google"] = "local"
    # The load balancer's static address: owners point their domains at it.
    # Unset: adding a domain is refused.
    DOMAINS_TARGET_IP: str | None = None
    # The TXT record proving which business owns a domain:
    # <label>.<domain>, its value a token per business and domain.
    DOMAINS_VERIFY_LABEL: str = "_sessionpilot"
    # Cloud Scheduler sends it in X-Domain-Check-Secret on every check.
    # Unset refuses every call.
    DOMAINS_CHECK_SECRET: str | None = None
    # Google Cloud (DOMAINS_PROVIDER=google): where the load balancer is and
    # the names of its parts (deploy/gcp/README.md, step 10).
    GCP_PROJECT_ID: str | None = None
    GCP_REGION: str = "australia-southeast1"
    LB_URL_MAP: str = "web"
    LB_HTTPS_PROXY: str = "web-https"
    LB_API_BACKEND: str = "api"
    LB_BASE_CERTIFICATE: str = "base-domain"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()