from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.response import ApiResponse
from app.dependencies.db import get_db
from app.dependencies.auth import resolve_location_id, get_current_token_context
from app.auth.jwt.context import TokenContext
from app.core.config import settings
from app.auth.services.auth import AuthService
from app.auth.schemas.auth import (
    LoginRequest,
    ResetPasswordRequest,
    ForgotPasswordRequest
)


router = APIRouter(
    prefix="/auth/v1",
    tags=["auth"],
)


@router.post("/login")
def login(
    body: LoginRequest,
    response: Response,
    location_id: UUID = Depends(
        resolve_location_id,
    ),
    db: Session = Depends(get_db),
) -> ApiResponse[None]:
    access_token = AuthService(db=db).login(
        body=body,
        location_id=location_id
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


@router.post("/forgot-password")
def forgot_password(
    body: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[None]:
    AuthService(db=db).request_password_reset(
        body=body
    )
    
    return ApiResponse(
        ok=True,
        msg="Please check your email",
        data=None
    )
    
    
@router.post("/reset-password")
def reset_password(
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[None]:
    AuthService(db=db).reset_password(
        body=body
    )
    
    return ApiResponse(
        ok=True,
        msg="Password reset",
        data=None
    )
    
    
@router.get("/session")
def get_session(
    ctx: TokenContext = Depends(
        get_current_token_context,
    ),
) -> ApiResponse[dict]:
    return ApiResponse(
        ok=True,
        msg="Authenticated",
        data={
            "user_id": str(ctx.user_id),
            "location_id": str(ctx.location_id),
            "email": ctx.email,
            "first_name": ctx.first_name,
            "roles": list(ctx.roles),
        },
    )