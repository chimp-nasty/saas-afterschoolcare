"""
What an uploaded image really is (Pillow reads it, whatever the browser
claimed): a business's logo and site icon (docs/tenant-administration.md,
stage 5). SVG never gets here: it isn't an image Pillow reads, and it can
carry script.
"""

from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError


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


# A photo's longest side once re-saved: sharp on a wide screen, small to load.
PHOTO_MAX_PIXELS = 2400


def prepare_photo(content: bytes) -> bytes | None:
    """
    A photo for the public site (docs/public-site.md, stage 9), re-saved as
    a JPEG at most PHOTO_MAX_PIXELS on its longest side, or None if it isn't
    a readable PNG, JPEG or WebP. Turned the way the camera meant first,
    then saved without any of its metadata: a phone photo's EXIF can hold
    where it was taken, and these may show children at a known place.
    """
    if check_image(content, allowed={"PNG", "JPEG", "WEBP"}) is None:
        return None

    try:
        with Image.open(BytesIO(content)) as opened:
            image = ImageOps.exif_transpose(opened)

            # Transparency (PNG, WebP) on white: JPEG has none.
            if image.mode in ("RGBA", "LA", "P"):
                image = image.convert("RGBA")
                background = Image.new("RGB", image.size, "white")
                background.paste(image, mask=image.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")

            image.thumbnail((PHOTO_MAX_PIXELS, PHOTO_MAX_PIXELS))

            output = BytesIO()
            # No exif= and no icc_profile=: nothing of the original's
            # metadata is written.
            image.save(output, format="JPEG", quality=85, optimize=True, progressive=True)
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        return None

    return output.getvalue()
