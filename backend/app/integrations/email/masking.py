def mask_email(email: str) -> str:
    """
    Enough of an address for support to recognise it, and no more:
    "jakson.b@gmail.com" -> "j***@gmail.com" (docs/email-policy.md, section 6).
    """
    local, _, domain = email.strip().rpartition("@")

    if not local or not domain:
        return "***"

    return f"{local[0]}***@{domain.lower()}"
