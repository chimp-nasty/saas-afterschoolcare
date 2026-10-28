"""
The platform's landing page (docs/platform-site.md): its words, colours,
logo and icon, photos and feature cards. Anyone reads them on the
platform's site; only the platform's admins change them, in place on the
page.
"""

import uuid
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import settings
from app.main import app
from tests.factories import Api, FakeStorage


BASE = "/platform-site/v1/"
PLATFORM_HOST = settings.BASE_DOMAIN

FEATURE = {"icon": "privacy", "title": "Only what's needed", "text": "Emails never carry health details."}


def _client(host: str = PLATFORM_HOST) -> TestClient:
    return TestClient(
        app,
        base_url=f"https://{host}/api",
        headers={
            "Origin": f"https://{host}",
            "X-Forwarded-For": f"10.252.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}",
        },
    )


def _image(width: int, height: int, image_format: str = "PNG") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), "#1B2A4A").save(buffer, format=image_format)

    return buffer.getvalue()


@pytest.fixture
def platform() -> TestClient:
    client = _client()
    response = client.post("/platform/v1/login", json={"email": "platform@test.com", "password": "123"})
    assert response.status_code == 200, response.text

    return client


@pytest.fixture
def site_restored(api: Api):
    """The platform's page is shared: put its row and features back afterwards."""
    [site] = api.sql("SELECT * FROM public.platform_site")
    features = api.sql("SELECT position, icon, title, description FROM public.platform_features ORDER BY position")

    yield

    columns = [c for c in site._fields if c not in ("id", "updated_at")]
    api.sql(
        f"UPDATE public.platform_site SET {', '.join(f'{c} = :{c}' for c in columns)}",
        **{c: getattr(site, c) for c in columns},
    )
    api.sql("DELETE FROM public.platform_features")

    for feature in features:
        api.sql(
            "INSERT INTO public.platform_features (position, icon, title, description) VALUES (:p, :i, :t, :d)",
            p=feature.position,
            i=feature.icon,
            t=feature.title,
            d=feature.description,
        )


def _upload(client: TestClient, kind: str, content: bytes, content_type: str):
    """Start an upload, play the browser sending the file, then confirm it."""
    started = client.post(f"{BASE}uploads", json={"kind": kind, "content_type": content_type})
    assert started.status_code == 200, started.text
    upload = started.json()["data"]

    assert FakeStorage.receive(upload, content)

    return client.post(f"{BASE}uploads/confirm", json={"kind": kind, "key": upload["key"]})


def _public() -> dict:
    return _client().get(BASE).json()["data"]


# Anyone reads the page on the platform's site, without logging in: the
# seeded headline and feature cards. A business's site doesn't have it.
def test_anyone_reads_the_page():
    response = _client().get(BASE)

    assert response.status_code == 200, response.text
    page = response.json()["data"]
    assert page["headline"]
    assert len(page["features"]) > 0
    assert page["has_logo"] is False

    assert _client(f"tenant1.{settings.BASE_DOMAIN}").get(BASE).status_code == 404


# A platform admin changes the words and colours; only what's sent changes,
# and something sent empty is cleared.
def test_platform_admins_edit_the_words(platform, site_restored):
    before = _public()

    response = platform.put(BASE, json={"headline": "Run your centres", "primary_color": "#1B2A4A"})
    assert response.status_code == 200, response.text

    page = _public()
    assert page["headline"] == "Run your centres"
    assert page["primary_color"] == "#1B2A4A"
    assert page["hero_text"] == before["hero_text"]

    assert platform.put(BASE, json={"about_title": ""}).status_code == 200
    assert _public()["about_title"] is None


# The feature cards are saved as a whole list, in order; at most 9, each
# with one of the page's icons.
def test_feature_cards(platform, site_restored):
    second = {"icon": "location", "title": "Your data stays in Australia", "text": "Stored in Australia."}

    response = platform.put(f"{BASE}features", json={"features": [FEATURE, second]})
    assert response.status_code == 200, response.text
    assert _public()["features"] == [FEATURE, second]

    assert platform.put(f"{BASE}features", json={"features": [FEATURE] * 10}).status_code == 422
    assert platform.put(f"{BASE}features", json={"features": [{**FEATURE, "icon": "rocket"}]}).status_code == 422
    assert platform.put(f"{BASE}features", json={"features": [{**FEATURE, "title": " "}]}).status_code == 422


# Nobody else changes it: without the platform's login it's refused (401),
# and a business's site has none of it (404).
def test_only_platform_admins_edit(api: Api, tenant2_owner):
    assert _client().put(BASE, json={"headline": "Hijacked"}).status_code == 401
    assert _client().put(f"{BASE}features", json={"features": [FEATURE]}).status_code == 401
    assert _client().post(f"{BASE}uploads", json={"kind": "logo", "content_type": "image/png"}).status_code == 401
    assert _client().delete(f"{BASE}files/logo").status_code == 401

    assert tenant2_owner.put(BASE, json={"headline": "Hijacked"}).status_code == 404


# A logo of any shape is saved and linked publicly; replacing it removes the
# old file. With no icon, the tab uses the logo; with neither, the app's.
def test_logo(api: Api, platform, site_restored):
    assert _client().get(f"{BASE}files/icon", follow_redirects=False).headers["location"] == "/favicon.svg"
    assert _client().get(f"{BASE}files/logo", follow_redirects=False).status_code == 404

    first = _upload(platform, "logo", _image(600, 150), "image/png")
    assert first.status_code == 200, first.text
    assert first.json()["data"]["has_logo"] is True

    [(first_key,)] = api.sql("SELECT logo_key FROM public.platform_site")
    assert first_key.startswith("branding/platform/logo/")

    assert _upload(platform, "logo", _image(400, 100, "JPEG"), "image/jpeg").status_code == 200
    assert (FakeStorage.bucket, first_key) not in FakeStorage.state.objects

    logo = _client().get(f"{BASE}files/logo", follow_redirects=False)
    icon = _client().get(f"{BASE}files/icon", follow_redirects=False)
    assert logo.status_code == 302
    assert logo.headers["location"].startswith("https://storage.test/")
    assert icon.headers["location"] == logo.headers["location"]


# The hero photo is re-saved as a JPEG with none of its metadata, shown
# with its description; removing it takes the description too. A file
# that isn't an image is refused, and the icon must be a square PNG.
def test_photos_and_icon(api: Api, platform, site_restored):
    exif = Image.Exif()
    exif[0x010E] = "Taken at the school gate"  # ImageDescription
    buffer = BytesIO()
    Image.new("RGB", (1200, 800), "#1B2A4A").save(buffer, format="JPEG", exif=exif)

    assert _upload(platform, "hero_photo", buffer.getvalue(), "image/jpeg").status_code == 200
    platform.put(BASE, json={"hero_photo_alt": "Children on the oval"})
    assert _public()["hero_photo"]["alt"] == "Children on the oval"

    [(key,)] = api.sql("SELECT hero_photo_key FROM public.platform_site")
    saved = Image.open(BytesIO(FakeStorage.state.objects[(FakeStorage.bucket, key)]["content"]))
    assert saved.format == "JPEG"
    assert len(saved.getexif()) == 0

    assert _upload(platform, "about_photo", b"%PDF-1.4 not a photo", "image/png").status_code == 400
    assert _upload(platform, "icon", _image(300, 200), "image/png").status_code == 400

    assert platform.delete(f"{BASE}files/hero_photo").status_code == 200
    assert _public()["hero_photo"] is None
    [(alt,)] = api.sql("SELECT hero_photo_alt FROM public.platform_site")
    assert alt is None


# An upload confirmed under another kind or outside the platform's own
# folder is refused (404).
def test_uploads_stay_in_their_place(platform):
    started = platform.post(f"{BASE}uploads", json={"kind": "logo", "content_type": "image/png"}).json()["data"]
    assert FakeStorage.receive(started, _image(100, 100))

    assert platform.post(f"{BASE}uploads/confirm", json={"kind": "hero_photo", "key": started["key"]}).status_code == 404
    assert platform.post(
        f"{BASE}uploads/confirm", json={"kind": "logo", "key": "pending/tenants/x/site/logo/y"}
    ).status_code == 404
