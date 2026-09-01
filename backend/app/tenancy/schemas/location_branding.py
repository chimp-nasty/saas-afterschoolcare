from pydantic import BaseModel


class PublicLocationResponse(BaseModel):
    tenant_name: str
    tenant_code: str

    location_code: str
    location_name: str

    display_name: str | None
    logo_key: str | None

    primary_color: str | None
    secondary_color: str | None
    font_family: str | None