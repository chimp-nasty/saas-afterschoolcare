from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool

from app.api.response import ApiResponse
from app.dependencies.db import get_db
from app.dependencies.service import get_service
from app.integrations.email.webhook import SesWebhookService


# Exempt from rate limiting (app/middleware/__init__.py). SNS signs every
# message; SesWebhookService rejects anything unsigned, forged, stale or
# from another topic.
router = APIRouter(
    prefix="/api/v1/webhooks",
    tags=["webhooks"],
)


@router.post("/ses")
async def ses_webhook(
    request: Request,
    service: SesWebhookService = Depends(
        get_service(
            SesWebhookService,
            db_dependency=get_db,
        )
    ),
) -> ApiResponse[None]:
    # SNS posts JSON as text/plain; read the raw body.
    payload = await request.body()

    # Blocking database and network work; keep it off the event loop.
    await run_in_threadpool(
        service.handle,
        payload=payload,
    )

    return ApiResponse(
        ok=True,
        msg="Webhook received",
        data=None,
    )
