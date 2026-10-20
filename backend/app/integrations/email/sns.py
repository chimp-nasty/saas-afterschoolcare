"""
Checking that an SNS message really came from AWS, for our topic, before
anything acts on it (https://docs.aws.amazon.com/sns/latest/dg/sns-verify-signature-of-message.html).

SNS signs a fixed set of the message's fields with a key whose certificate
it publishes at SigningCertURL. We only fetch certificates from an
sns.<region>.amazonaws.com host over HTTPS, only accept our own topic, and
refuse messages older than an hour (replays).
"""

import base64
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from urllib.parse import urlparse

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding


_SNS_HOST = re.compile(r"^sns\.[a-z0-9-]+\.amazonaws\.com$")

_MAX_AGE = timedelta(hours=1)

# The fields each message type signs, in the order they're signed.
_SIGNED_FIELDS = {
    "Notification": ("Message", "MessageId", "Subject", "Timestamp", "TopicArn", "Type"),
    "SubscriptionConfirmation": ("Message", "MessageId", "SubscribeURL", "Timestamp", "Token", "TopicArn", "Type"),
    "UnsubscribeConfirmation": ("Message", "MessageId", "SubscribeURL", "Timestamp", "Token", "TopicArn", "Type"),
}

_HASHES = {"1": hashes.SHA1, "2": hashes.SHA256}


class InvalidSnsMessage(Exception):
    """Not a genuine, current SNS message for our topic."""


def is_sns_url(url: str) -> bool:
    """An HTTPS address on an SNS host (certificates, subscription links)."""
    parsed = urlparse(url)

    return parsed.scheme == "https" and bool(_SNS_HOST.match(parsed.hostname or ""))


@lru_cache(maxsize=16)
def fetch_certificate(url: str) -> bytes:
    """SNS's signing certificate (PEM). Cached: SNS reuses it for months."""
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.read()


def verify(message: dict, *, topic_arn: str | None) -> None:
    """Raise InvalidSnsMessage unless `message` is genuine, current and ours."""
    message_type = message.get("Type")
    signed_fields = _SIGNED_FIELDS.get(message_type)

    if signed_fields is None:
        raise InvalidSnsMessage(f"unknown type {message_type!r}")

    if not topic_arn or message.get("TopicArn") != topic_arn:
        raise InvalidSnsMessage("not our topic")

    hash_type = _HASHES.get(str(message.get("SignatureVersion")))
    cert_url = message.get("SigningCertURL", "")

    if hash_type is None:
        raise InvalidSnsMessage("unknown signature version")

    if not is_sns_url(cert_url) or not urlparse(cert_url).path.endswith(".pem"):
        raise InvalidSnsMessage("certificate not from SNS")

    try:
        sent_at = datetime.fromisoformat(message["Timestamp"].replace("Z", "+00:00"))
    except (KeyError, ValueError) as exc:
        raise InvalidSnsMessage("bad timestamp") from exc

    if datetime.now(timezone.utc) - sent_at > _MAX_AGE:
        raise InvalidSnsMessage("too old")

    # "Key\nValue\n" for each signed field present, in order.
    string_to_sign = "".join(
        f"{field}\n{message[field]}\n"
        for field in signed_fields
        if field in message
    ).encode("utf-8")

    try:
        certificate = x509.load_pem_x509_certificate(fetch_certificate(cert_url))
        certificate.public_key().verify(
            base64.b64decode(message["Signature"]),
            string_to_sign,
            padding.PKCS1v15(),
            hash_type(),
        )
    except (InvalidSignature, KeyError, ValueError) as exc:
        raise InvalidSnsMessage("bad signature") from exc
    except OSError as exc:
        raise InvalidSnsMessage("certificate unavailable") from exc
