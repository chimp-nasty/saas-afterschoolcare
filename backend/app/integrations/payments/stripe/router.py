from fastapi import APIRouter, Depends, Header, Request
from starlette.concurrency import run_in_threadpool

from app.api.response import ApiResponse
from app.dependencies.db import get_db
from app.dependencies.service import get_service
from app.integrations.payments.stripe.webhook import StripeWebhookService


# Exempt from rate limiting (app/middleware/__init__.py). Stripe signs every
# request; StripeWebhookService rejects anything unsigned or forged.
router = APIRouter(
    prefix="/v1/webhooks",
    tags=["webhooks"],
)


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None),
    service: StripeWebhookService = Depends(
        get_service(
            StripeWebhookService,
            db_dependency=get_db,
        )
    ),
) -> ApiResponse[None]:
    # The signature covers the raw bytes, so read them before any parsing.
    payload = await request.body()

    # The service does blocking database work; keep it off the event loop.
    await run_in_threadpool(
        service.handle,
        payload=payload,
        signature=stripe_signature,
    )

    return ApiResponse(
        ok=True,
        msg="Webhook received",
        data=None,
    )


# Stripe Connect: events on tenants' connected accounts (their checkouts
# and refunds, account updates), signed with the Connect endpoint's secret.
@router.post("/stripe/connect")
async def stripe_connect_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None),
    service: StripeWebhookService = Depends(
        get_service(
            StripeWebhookService,
            db_dependency=get_db,
        )
    ),
) -> ApiResponse[None]:
    payload = await request.body()

    await run_in_threadpool(
        service.handle,
        payload=payload,
        signature=stripe_signature,
        connect=True,
    )

    return ApiResponse(
        ok=True,
        msg="Webhook received",
        data=None,
    )
