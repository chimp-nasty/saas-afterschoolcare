from pydantic import BaseModel, EmailStr, Field


class AccountRoleResponse(BaseModel):
    """One of your roles at one of your locations."""

    location_code: str
    location_name: str
    role_code: str
    role_name: str


class AccountResponse(BaseModel):
    """Your own account, read-only: admins correct names, and email is the login."""

    email: EmailStr
    first_name: str
    last_name: str
    # At this tenant's locations only.
    roles: list[AccountRoleResponse]


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
