from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.api.response import ApiResponse
from app.dependencies.db import get_db
from app.dependencies.auth import (
    resolve_location_id,
    get_current_token_context,
)
from app.dependencies.service import get_service
from app.auth.jwt.context import TokenContext
from app.core.config import settings
from app.auth.services.auth import AuthService
from app.auth.schemas.auth import (
    LoginRequest,
    ResetPasswordRequest,
    ForgotPasswordRequest,
    SessionResponse,
)


router = APIRouter(
    prefix="/auth/v1",
    tags=["auth"],
)


@router.post("/login/{location_code}")
def login(
    body: LoginRequest,
    response: Response,
    location_id: UUID = Depends(
        resolve_location_id,
    ),
    service: AuthService = Depends(
        get_service(
            AuthService,
            db_dependency=get_db,
        )
    ),
) -> ApiResponse[None]:
    access_token = service.login(
        body=body,
        location_id=location_id,
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
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


@router.post("/logout")
def logout(
    response: Response,
) -> ApiResponse[None]:
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )

    return ApiResponse(
        ok=True,
        msg="Logged out",
        data=None,
    )


# Per location, like login: the reset email comes from that centre and
# links back to its site.
@router.post("/forgot-password/{location_code}")
def forgot_password(
    body: ForgotPasswordRequest,
    location_id: UUID = Depends(
        resolve_location_id,
    ),
    service: AuthService = Depends(
        get_service(
            AuthService,
            db_dependency=get_db,
        )
    ),
) -> ApiResponse[None]:
    service.request_password_reset(
        body=body,
        location_id=location_id,
    )

    return ApiResponse(
        ok=True,
        msg="Please check your email",
        data=None,
    )


@router.post("/reset-password")
def reset_password(
    body: ResetPasswordRequest,
    service: AuthService = Depends(
        get_service(
            AuthService,
            db_dependency=get_db,
        )
    ),
) -> ApiResponse[None]:
    service.reset_password(
        body=body
    )

    return ApiResponse(
        ok=True,
        msg="Password reset",
        data=None,
    )


@router.get("/session")
def get_session(
    ctx: TokenContext = Depends(
        get_current_token_context,
    ),
    service: AuthService = Depends(
        get_service(
            AuthService,
            db_dependency=get_db,
        )
    ),
) -> ApiResponse[SessionResponse]:
    return ApiResponse(
        ok=True,
        msg="Session retrieved",
        data=service.get_session(ctx=ctx),
    )
