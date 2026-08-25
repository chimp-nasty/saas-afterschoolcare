import hashlib
import hmac
import secrets

from pwdlib import PasswordHash

from app.core.config import settings


password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(
    password: str,
    hashed_password: str,
) -> bool:
    return password_hash.verify(
        password,
        hashed_password,
    )

def generate_password_reset_token() -> str:
    return secrets.token_urlsafe(48)

def hash_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8"),
    ).hexdigest()

def hash_email(email: str) -> str | None:
    normalized = email.strip().lower()

    if not settings.EMAIL_HASH_SECRET:
        return None

    return hmac.new(
        settings.EMAIL_HASH_SECRET.encode("utf-8"),
        normalized.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()