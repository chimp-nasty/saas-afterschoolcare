"""
Each tenant's site carries its own API under /api: the host decides the
tenant, a login only counts on the site it was made on, and changes must
come from that same site (docs/tenant-administration.md, stage 1).
"""

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from tests.factories import PASSWORD, Api


def _bare_client(host: str, **headers: str) -> TestClient:
    """A client for a host, sending only the headers given (no Origin)."""
    return TestClient(app, base_url=f"https://{host}/api", headers=headers)


# A login made on tenant 1's site doesn't work on tenant 2's site, even
# with the same token.
def test_token_is_refused_on_another_tenants_site(api: Api, customer):
    token = customer.client.cookies.get("access_token")
    tenant2 = api.client(tenant="tenant2")

    response = tenant2.get(
        "/auth/v1/session",
        headers={"Cookie": f"access_token={token}"},
    )

    assert customer.client.get("/auth/v1/session").status_code == 200
    assert response.status_code == 401


# A host that isn't a tenant's site finds no tenant, so nobody can log in
# there.
def test_unknown_host_finds_no_tenant(api: Api, customer):
    for host in (f"nobody.{settings.BASE_DOMAIN}", "example.com"):
        client = _bare_client(host, Origin=f"https://{host}")

        response = client.post(
            "/auth/v1/login/location1",
            json={"email": customer.email, "password": PASSWORD},
        )

        assert response.status_code == 404


# A change sent without an Origin, or from another site (including another
# tenant's), is refused before it reaches the API.
def test_changes_must_come_from_the_same_site(api: Api, customer):
    host = f"tenant1.{settings.BASE_DOMAIN}"
    body = {"email": customer.email, "password": PASSWORD}

    for headers in (
        {},
        {"Origin": "https://evil.example.com"},
        {"Origin": f"https://tenant2.{settings.BASE_DOMAIN}"},
        {"Origin": f"https://{host}:8443"},
    ):
        response = _bare_client(host, **headers).post("/auth/v1/login/location1", json=body)

        assert response.status_code == 403
        assert response.json()["msg"] == "This request didn't come from this site."

    same_site = _bare_client(host, Origin=f"https://{host}")
    assert same_site.post("/auth/v1/login/location1", json=body).status_code == 200


# Reading needs no Origin (browsers leave it off same-site GETs).
def test_reads_need_no_origin(api: Api):
    client = _bare_client(f"tenant1.{settings.BASE_DOMAIN}")

    assert client.get("/location-branding/v1/public/location1").status_code == 200


# Webhooks come from Stripe and SES with no Origin, and still reach their
# handlers (here refused as malformed, not as cross-site).
def test_webhooks_need_no_origin(api: Api):
    client = _bare_client(f"tenant1.{settings.BASE_DOMAIN}")

    assert client.post("/v1/webhooks/ses", content=b"not json").status_code == 400
    assert client.post("/v1/webhooks/stripe", content=b"{}").status_code != 403


# The login cookie has no Domain, so it belongs to the one site that set it.
def test_login_cookie_belongs_to_one_site(api: Api, customer):
    response = api.client().post(
        "/auth/v1/login/location1",
        json={"email": customer.email, "password": PASSWORD},
    )

    set_cookie = response.headers["set-cookie"].lower()

    assert "access_token=" in set_cookie
    assert "domain=" not in set_cookie
