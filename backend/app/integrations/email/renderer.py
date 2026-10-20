"""
Turns an email definition, a centre, the values for its placeholders and an
optional tenant override into a finished subject, HTML and plain text.

Tenant wording is plain text: {placeholder} is replaced with its value
(only the email's whitelisted placeholders; anything else is left as
typed) and the result is escaped like any other value. It never goes
through Jinja, so it can't reach template logic. Jinja only renders our own
layout and locked blocks (templates/), with autoescaping on for HTML.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from app.integrations.email.catalogue import EmailDefinition


_TEMPLATES = Path(__file__).parent / "templates"

_environment = Environment(
    loader=FileSystemLoader(_TEMPLATES),
    autoescape=select_autoescape(enabled_extensions=("html",), default_for_string=False),
    undefined=StrictUndefined,
    keep_trailing_newline=True,
)

_PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")

# A brand colour safe to put in a style attribute; anything else falls
# back to the default.
_COLOUR = re.compile(r"^#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?$")
_DEFAULT_COLOUR = "#27272a"


@dataclass(frozen=True)
class Centre:
    """Who the email is from: the location, as families know it."""

    name: str
    email: str | None
    phone: str | None
    primary_color: str | None


@dataclass(frozen=True)
class Override:
    """A tenant's own wording; a blank slot keeps the default."""

    subject: str | None = None
    heading: str | None = None
    body: str | None = None
    sign_off: str | None = None


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    html: str
    text: str


def fill(text: str, values: dict[str, str], allowed: frozenset[str]) -> str:
    """Replace each allowed {placeholder}; leave anything else as written."""

    def replace(match: re.Match) -> str:
        name = match.group(1)

        if name in allowed and name in values:
            return values[name]

        return match.group(0)

    return _PLACEHOLDER.sub(replace, text)


def _slot(override: Override | None, name: str, default: str) -> str:
    value = getattr(override, name) if override else None

    return value if value and value.strip() else default


def render(
    definition: EmailDefinition,
    *,
    centre: Centre,
    values: dict[str, str],
    block: dict[str, Any],
    override: Override | None = None,
) -> RenderedEmail:
    """
    `values` fill the placeholders in the wording (first_name, centre_name
    and the email's own); `block` holds what the locked block shows (links,
    the PIN, amounts).
    """
    allowed = definition.allowed_placeholders
    values = {**values, "centre_name": centre.name}

    def slot(name: str) -> str:
        return fill(_slot(override, name, getattr(definition, name)), values, allowed).strip()

    # One line, whatever was typed.
    subject = " ".join(slot("subject").split())
    body = slot("body")

    context = {
        "email_type": definition.type.value,
        "subject": subject,
        "heading": slot("heading"),
        "paragraphs": [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()],
        "sign_off": slot("sign_off"),
        "footer_reason": fill(definition.footer_reason, values, allowed),
        "centre": centre,
        "colour": centre.primary_color if centre.primary_color and _COLOUR.match(centre.primary_color) else _DEFAULT_COLOUR,
        **block,
    }

    return RenderedEmail(
        subject=subject,
        html=_environment.get_template("layout.html").render(context),
        text=_environment.get_template("layout.txt").render(context),
    )
