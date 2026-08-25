from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from fastapi import Response

from app.api.response import ApiResponse
from app.dependencies.db import get_db
from app.core.config import settings


@router.post("/login")
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> ApiResponse[None]:
    result = LoginService(db).execute(
        payload=payload,
    )

    response.set_cookie(
        key="access_token",
        value=result.access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
        max_age=(
            settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            * 60
        ),
    )

    return ApiResponse(
        ok=True,
        msg="Login successful",
        data=None,
    )