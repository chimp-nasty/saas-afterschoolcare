"""
What an uploaded image really is (Pillow reads it, whatever the browser
claimed): a business's logo and site icon (docs/tenant-administration.md,
stage 5). SVG never gets here: it isn't an image Pillow reads, and it can
carry script.
"""

from dataclasses import dataclass
from io import BytesIO

from PIL import Image, UnidentifiedImageError


# A 1 MB file can still claim to be enormous once decoded; refuse anything
# beyond a large photo's pixels rather than decode it.
Image.MAX_IMAGE_PIXELS = 40_000_000

_FORMATS = {
    "PNG": ("image/png", "png"),
    "JPEG": ("image/jpeg", "jpg"),
    "WEBP": ("image/webp", "webp"),
}


@dataclass(frozen=True)
class CheckedImage:
    content_type: str
    extension: str
    width: int
    height: int


def check_image(content: bytes, *, allowed: set[str]) -> CheckedImage | None:
    """The image's type and size if it's a readable image of an allowed format ("PNG", "JPEG", "WEBP"), else None."""
    try:
        with Image.open(BytesIO(content)) as image:
            image_format = image.format
            width, height = image.size
            image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        return None

    if image_format not in allowed or image_format not in _FORMATS:
        return None

    content_type, extension = _FORMATS[image_format]

    return CheckedImage(content_type=content_type, extension=extension, width=width, height=height)
