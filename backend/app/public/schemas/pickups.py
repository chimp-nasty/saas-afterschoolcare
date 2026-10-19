from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.public.schemas.enums import PickupRelation
from app.public.schemas.phone import normalise_au_phone


class PickupResponse(BaseModel):
    """
    A person on the family's pickup list. The ID check and kiosk state are
    shown as yes/no only: never who checked, when, or anything about the PIN.
    """

    id: UUID

    first_name: str
    last_name: str
    phone: str

    relation: PickupRelation
    relation_other: str | None

    # The account holder's own row: kept in sync with their profile, and not
    # editable or removable here.
    is_account_holder: bool

    identity_verified: bool

    # False while they're still on the default kiosk PIN.
    kiosk_pin_set: bool

    created_at: datetime


def _strip_name(value: str | None) -> str | None:
    return value.strip() if value is not None else None


def _check_relation(relation: PickupRelation | None, relation_other: str | None) -> None:
    if relation == PickupRelation.ACCOUNT_HOLDER:
        raise ValueError("The account holder is added automatically")

    if relation == PickupRelation.OTHER and not relation_other:
        raise ValueError("Describe the relationship")


class CreatePickupRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str

    relation: PickupRelation
    relation_other: str | None = Field(default=None, max_length=100)

    # Both declarations must be ticked to add someone.
    consent_confirmed: Literal[True]
    adult_confirmed: Literal[True]

    _strip_names = field_validator("first_name", "last_name")(_strip_name)

    @field_validator("phone")
    @classmethod
    def _normalise_phone(cls, value: str) -> str:
        return normalise_au_phone(value)

    @field_validator("relation_other")
    @classmethod
    def _blank_to_none(cls, value: str | None) -> str | None:
        return (value or "").strip() or None

    @model_validator(mode="after")
    def _relation(self) -> "CreatePickupRequest":
        _check_relation(self.relation, self.relation_other)

        # Only "other" keeps its own wording.
        if self.relation != PickupRelation.OTHER:
            self.relation_other = None

        return self


class UpdatePickupRequest(BaseModel):
    """
    Only the fields sent are updated. A new name or phone means staff check
    their ID again; a new phone also resets their kiosk PIN (schema/0004).
    """

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = None

    relation: PickupRelation | None = None
    relation_other: str | None = Field(default=None, max_length=100)

    _strip_names = field_validator("first_name", "last_name")(_strip_name)

    @field_validator("phone")
    @classmethod
    def _normalise_phone(cls, value: str | None) -> str | None:
        return normalise_au_phone(value) if value is not None else None

    @field_validator("relation_other")
    @classmethod
    def _blank_to_none(cls, value: str | None) -> str | None:
        return (value or "").strip() or None

    @model_validator(mode="after")
    def _relation(self) -> "UpdatePickupRequest":
        if "relation" in self.model_fields_set:
            _check_relation(self.relation, self.relation_other)

            if self.relation != PickupRelation.OTHER:
                self.relation_other = None
                self.model_fields_set.add("relation_other")

        return self
