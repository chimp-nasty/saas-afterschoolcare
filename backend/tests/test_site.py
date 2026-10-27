"""
The business's site (docs/tenant-administration.md, stage 5): its landing
page's words, colours, logo and icon, FAQs and policy PDFs, set by its
owner in Business settings › Your site and shown to anyone.
"""

from io import BytesIO

import pytest
from PIL import Image

from tests.factories import Api, FakeStorage


PDF = b"%PDF-1.4\n%test policy\n"


def _image(width: int, height: int, image_format: str = "PNG") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), "#5E2BFF").save(buffer, format=image_format)

    return buffer.getvalue()


@pytest.fixture
def site_restored(api: Api):
    """Tenant2's site is shared: put its branding, tagline and FAQs back afterwards."""
    [branding] = api.sql(
        "SELECT b.primary_color, b.secondary_color, b.accent_color FROM tenancy.tenant_branding b "
        "JOIN tenancy.tenants t ON t.id = b.tenant_id WHERE t.code = 'tenant2'"
    )

    yield

    api.sql(
        "UPDATE tenancy.tenant_branding SET primary_color = :p, secondary_color = :s, accent_color = :a, "
        "logo_key = NULL, icon_key = NULL "
        "WHERE tenant_id = (SELECT id FROM tenancy.tenants WHERE code = 'tenant2')",
        p=branding.primary_color,
        s=branding.secondary_color,
        a=branding.accent_color,
    )
    api.sql("UPDATE tenancy.tenants SET tagline = NULL WHERE code = 'tenant2'")
    api.sql("DELETE FROM tenancy.tenant_faqs WHERE tenant_id = (SELECT id FROM tenancy.tenants WHERE code = 'tenant2')")


def _upload(client, kind: str, content: bytes, content_type: str):
    """Start an upload, play the browser sending the file, then confirm it."""
    started = client.post("/business/v1/site/uploads", json={"kind": kind, "content_type": content_type})
    assert started.status_code == 200, started.text
    upload = started.json()["data"]

    assert FakeStorage.receive(upload, content)

    return client.post("/business/v1/site/uploads/confirm", json={"kind": kind, "key": upload["key"]})


def _public(api: Api, tenant: str = "tenant2"):
    return api.client(tenant=tenant).get("/location-branding/v1/public/business").json()["data"]


# The owner's headline, colours and FAQs show on the landing page, in their
# order; another business's page doesn't show them.
def test_landing_page_content(api: Api, tenant2_owner, site_restored):
    assert tenant2_owner.put(
        "/business/v1/site",
        json={
            "tagline": "Care made easy",
            "primary_color": "#112233",
            "secondary_color": "#AABBCC",
            "accent_color": "#F59E0B",
        },
    ).status_code == 200
    assert tenant2_owner.put(
        "/business/v1/site/faqs",
        json={"faqs": [{"question": "When?", "answer": "After school."}, {"question": "Where?", "answer": "Here."}]},
    ).status_code == 200

    page = _public(api)

    assert page["tagline"] == "Care made easy"
    assert page["primary_color"] == "#112233"
    assert page["accent_color"] == "#F59E0B"
    assert [faq["question"] for faq in page["faqs"]] == ["When?", "Where?"]
    assert _public(api, "tenant1")["tagline"] is None
    assert _public(api, "tenant1")["faqs"] == []


# Every centre's pages use the business's colours.
def test_centres_use_the_business_colours(api: Api, tenant2_owner, site_restored):
    tenant2_owner.put("/business/v1/site", json={"primary_color": "#123456", "accent_color": "#654321"})

    location = api.client(tenant="tenant2").get("/location-branding/v1/public/location2").json()["data"]

    assert location["primary_color"] == "#123456"
    assert location["accent_color"] == "#654321"


# Only the owner changes the site: an admin gets 403.
def test_only_the_owner_changes_the_site(tenant2_admin):
    assert tenant2_admin.put("/business/v1/site", json={"tagline": "Taken over"}).status_code == 403
    assert tenant2_admin.put("/business/v1/site/faqs", json={"faqs": []}).status_code == 403
    assert tenant2_admin.post(
        "/business/v1/site/uploads", json={"kind": "logo", "content_type": "image/png"}
    ).status_code == 403


# Colours are #RRGGBB, at most 20 questions, and SVG isn't accepted.
def test_site_values_are_checked(tenant2_owner):
    faq = {"question": "Q?", "answer": "A."}

    assert tenant2_owner.put("/business/v1/site", json={"primary_color": "purple"}).status_code == 422
    assert tenant2_owner.put("/business/v1/site", json={"accent_color": "#FFF"}).status_code == 422
    assert tenant2_owner.put("/business/v1/site/faqs", json={"faqs": [faq] * 21}).status_code == 422
    assert tenant2_owner.post(
        "/business/v1/site/uploads", json={"kind": "logo", "content_type": "image/svg+xml"}
    ).status_code == 422


# A logo of any shape is saved and linked publicly; replacing it removes
# the old file. With no icon, the tab uses the logo.
def test_logo(api: Api, tenant2_owner, site_restored):
    first = _upload(tenant2_owner, "logo", _image(600, 150), "image/png")
    assert first.status_code == 200, first.text
    assert first.json()["data"]["has_logo"] is True
    assert _public(api)["has_logo"] is True

    [(first_key,)] = api.sql(
        "SELECT logo_key FROM tenancy.tenant_branding WHERE tenant_id = (SELECT id FROM tenancy.tenants WHERE code = 'tenant2')"
    )
    assert _upload(tenant2_owner, "logo", _image(400, 100, "JPEG"), "image/jpeg").status_code == 200
    assert (FakeStorage.bucket, first_key) not in FakeStorage.state.objects

    public = api.client(tenant="tenant2")
    logo = public.get("/location-branding/v1/site-files/logo", follow_redirects=False)
    icon = public.get("/location-branding/v1/site-files/icon", follow_redirects=False)

    assert logo.status_code == 302
    assert logo.headers["location"].startswith("https://storage.test/")
    assert icon.headers["location"] == logo.headers["location"]


# The site icon must be a square PNG of at least 192 pixels; a file that
# isn't an image is refused and removed.
def test_icon_is_checked(api: Api, tenant2_owner, site_restored):
    wide = _upload(tenant2_owner, "icon", _image(400, 200), "image/png")
    small = _upload(tenant2_owner, "icon", _image(64, 64), "image/png")
    jpeg = _upload(tenant2_owner, "icon", _image(256, 256, "JPEG"), "image/png")
    not_an_image = _upload(tenant2_owner, "icon", b"<svg onload=alert(1)>", "image/png")

    assert (wide.status_code, small.status_code) == (400, 400)
    assert wide.json()["msg"] == "The site icon must be square and at least 192 by 192 pixels"
    assert (jpeg.status_code, not_an_image.status_code) == (400, 400)
    assert not any(key.startswith("pending/") for _, key in FakeStorage.state.objects)

    assert _upload(tenant2_owner, "icon", _image(256, 256), "image/png").status_code == 200
    assert tenant2_owner.get("/business/v1/site").json()["data"]["has_icon"] is True


# With no icon or logo at all, the tab gets the platform's own icon; the
# logo and policies just aren't there.
def test_nothing_uploaded(api: Api):
    public = api.client(tenant="tenant1")

    assert public.get("/location-branding/v1/site-files/icon", follow_redirects=False).headers["location"] == "/favicon.svg"
    assert public.get("/location-branding/v1/site-files/logo").status_code == 404
    assert public.get("/location-branding/v1/site-files/privacy").status_code == 404


# Each policy upload is a new version and the public link serves the
# latest; a file that isn't a PDF is refused.
def test_policies_are_versioned(api: Api, tenant2_owner):
    assert _upload(tenant2_owner, "privacy", b"not a pdf", "application/pdf").status_code == 400

    assert _upload(tenant2_owner, "privacy", PDF, "application/pdf").status_code == 200
    assert _upload(tenant2_owner, "privacy", PDF + b"v2", "application/pdf").status_code == 200

    keys = api.sql(
        "SELECT storage_key FROM tenancy.tenant_documents WHERE kind = 'privacy' "
        "AND tenant_id = (SELECT id FROM tenancy.tenants WHERE code = 'tenant2') ORDER BY uploaded_at DESC"
    )
    assert len(keys) >= 2

    link = api.client(tenant="tenant2").get("/location-branding/v1/site-files/privacy", follow_redirects=False)
    assert link.headers["location"].endswith(f"{keys[0].storage_key}?signed")
    assert _public(api)["has_privacy"] is True


# A family signing up accepts the business's current terms, which stay on
# record against them; without any terms, nothing is recorded.
def test_sign_up_records_the_terms(api: Api, tenant2_owner):
    assert _upload(tenant2_owner, "terms", PDF, "application/pdf").status_code == 200
    [(current,)] = api.sql(
        "SELECT id::text FROM tenancy.tenant_documents WHERE kind = 'terms' "
        "AND tenant_id = (SELECT id FROM tenancy.tenants WHERE code = 'tenant2') ORDER BY uploaded_at DESC LIMIT 1"
    )

    family = api.new_customer(tenant="tenant2", location="location2")
    other = api.new_customer()

    [(accepted,)] = api.sql(
        "SELECT p.terms_document_id::text FROM public.customer_profile p JOIN auth.users u ON u.id = p.user_id WHERE u.email = :e",
        e=family.email,
    )
    [(none,)] = api.sql(
        "SELECT p.terms_document_id FROM public.customer_profile p JOIN auth.users u ON u.id = p.user_id WHERE u.email = :e",
        e=other.email,
    )

    assert accepted == current
    assert none is None
