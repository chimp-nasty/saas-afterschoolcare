# What a file really is, from its first bytes ("magic numbers"), whatever
# type the browser claimed for it.

# Enough bytes to recognise every type below.
SIGNATURE_LENGTH = 12

# HEIF brands an iPhone photo (or HEIC export) can carry.
_HEIC_BRANDS = {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1"}


def detect_content_type(head: bytes) -> str | None:
    """The file's content type, if it's a PDF, JPEG, PNG or HEIC image."""
    if head.startswith(b"%PDF-"):
        return "application/pdf"

    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    if head[4:8] == b"ftyp" and head[8:12] in _HEIC_BRANDS:
        return "image/heic"

    return None
