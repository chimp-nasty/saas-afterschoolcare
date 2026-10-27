"""
Custom domains (docs/tenant-administration.md, section 7): a business's
owner adds its main domain and domains sending visitors to it (Business
settings › Domains); the domain check (Cloud Scheduler, or the owner's
"Check now") proves each one, gets the business's certificate onto the load
balancer, and puts the site on the main domain. Google and DNS are the fake
(FakeDomains).
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.cache.stores import cache_stores
from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from tests.factories import Api, FakeDomains


SECRET = "test-domain-check-secret"


@pytest.fixture(autouse=True)
def domains_cleared(api: Api):
    """Domains belong to the shared tenants: remove them all afterwards."""
    yield

    api.sql("DELETE FROM tenancy.tenant_domains")
    api.sql("DELETE FROM tenancy.tenant_certificates")
    api.sql("UPDATE tenancy.tenants SET custom_domain = NULL WHERE custom_domain IS NOT NULL")
    cache_stores.location_branding.clear()


def _hostname() -> str:
    return f"care-{uuid.uuid4().hex[:8]}.example.com.au"


def _site_client(host: str, **headers: str) -> TestClient:
    return TestClient(
        app,
        base_url=f"https://{host}/api",
        headers={"Origin": f"https://{host}", "X-Forwarded-For": f"10.251.{uuid.uuid4().int % 250}.1", **headers},
    )


def _check(secret: str = SECRET, host: str | None = None):
    """The scheduled check, as Cloud Scheduler calls it (no Origin)."""
    client = TestClient(app, base_url=f"https://{host or settings.BASE_DOMAIN}/api")

    return client.post("/internal/v1/domain-check", headers={"X-Domain-Check-Secret": secret})


def _run_check() -> None:
    response = _check()
    assert response.status_code == 200, response.text


def _add(owner: TestClient, hostname: str, *, is_main: bool = True, include_www: bool = True) -> dict:
    response = owner.post("/business/v1/domains", json={"hostname": hostname, "is_main": is_main, "include_www": include_www})
    assert response.status_code == 201, response.text

    return response.json()["data"]


def _listing(owner: TestClient) -> dict:
    response = owner.get("/business/v1/domains")
    assert response.status_code == 200, response.text

    return response.json()["data"]


def _domain(owner: TestClient, hostname: str) -> dict:
    return next(d for d in _listing(owner)["domains"] if d["hostname"] == hostname)


def _make_live(owner: TestClient, hostname: str, **options) -> dict:
    """Add a domain and take it live: records, proof, certificate, load balancer."""
    domain = _add(owner, hostname, **options)
    FakeDomains.publish(domain)

    _run_check()  # proven; certificate requested
    FakeDomains.issue_all()
    _run_check()  # certificate issued and attached
    _run_check()  # live

    live = _domain(owner, hostname)
    assert live["state"] == "active", live

    return live


# Adding a main domain shows the records to add (TXT proof, Google's CNAME,
# the address, and the same for www); once they're found and the
# certificate is on the load balancer, the site lives on the domain: the
# API answers there for the business, its generated host and www redirect to
# it, and the platform's list shows it.
def test_main_domain_goes_live(api: Api, tenant2_owner):
    hostname = _hostname()
    domain = _add(tenant2_owner, hostname)

    assert domain["state"] == "pending_dns"
    assert [(r["type"], r["name"]) for r in domain["records"]] == [
        ("TXT", f"{settings.DOMAINS_VERIFY_LABEL}.{hostname}"),
        ("CNAME", domain["records"][1]["name"]),
        ("A", hostname),
        ("CNAME", domain["records"][3]["name"]),
        ("A", f"www.{hostname}"),
    ]
    assert domain["records"][2]["value"] == settings.DOMAINS_TARGET_IP

    FakeDomains.publish(domain)
    _run_check()

    assert _domain(tenant2_owner, hostname)["state"] == "verified"
    [certificate] = FakeDomains.state.certificates.values()
    assert certificate["hostnames"] == sorted([hostname, f"www.{hostname}"])

    FakeDomains.issue_all()
    _run_check()
    _run_check()

    listing = _listing(tenant2_owner)
    assert listing["live_domain"] == hostname
    assert [d["state"] for d in listing["domains"]] == ["active"]

    on_domain = _site_client(hostname).get("/location-branding/v1/public/business")
    on_generated = api.client(tenant="tenant2").get("/location-branding/v1/public/business")
    assert on_domain.status_code == 200, on_domain.text
    assert on_domain.json()["data"]["name"] == on_generated.json()["data"]["name"]

    routing = FakeDomains.state.routing
    assert routing["certificates"] == list(FakeDomains.state.certificates)
    assert routing["redirects"]["tenant2"] == {
        "hosts": sorted([f"tenant2.{settings.BASE_DOMAIN}", f"www.{hostname}"]),
        "target": hostname,
    }


# A domain stays pending until every record it needs is found, and the
# owner sees which ones were.
def test_records_needed_before_verifying(tenant2_owner):
    hostname = _hostname()
    domain = _add(tenant2_owner, hostname, include_www=False)

    _run_check()
    checked = _domain(tenant2_owner, hostname)
    assert checked["state"] == "pending_dns"
    assert [r["seen"] for r in checked["records"]] == [False, False, False]

    FakeDomains.state.txt[domain["records"][0]["name"]] = domain["records"][0]["value"]
    _run_check()
    checked = _domain(tenant2_owner, hostname)
    assert checked["state"] == "pending_dns"
    assert [r["seen"] for r in checked["records"]] == [True, False, False]
    assert FakeDomains.state.certificates == {}


# Two businesses may claim a domain while it's pending; the first to prove
# it with its TXT record gets it, and the other is told.
def test_first_business_to_prove_a_domain_gets_it(owner, tenant2_owner):
    hostname = _hostname()
    theirs = _add(tenant2_owner, hostname)
    ours = _add(owner, hostname)

    FakeDomains.publish(theirs)
    _run_check()
    FakeDomains.publish(ours)
    _run_check()

    assert _domain(tenant2_owner, hostname)["state"] == "verified"

    claimed = _domain(owner, hostname)
    assert claimed["state"] == "pending_dns"
    assert claimed["failure_reason"] == "Another business has already set up this domain."


# The platform's own addresses can't be added, and a domain is written the
# way DNS writes it whatever the owner typed (www isn't doubled).
def test_domain_names(tenant2_owner):
    for hostname in (f"tenant1.{settings.BASE_DOMAIN}", f"book.tenant1.{settings.BASE_DOMAIN}"):
        response = tenant2_owner.post("/business/v1/domains", json={"hostname": hostname, "is_main": True})
        assert response.status_code == 400, response.text

    assert tenant2_owner.post("/business/v1/domains", json={"hostname": "not a domain", "is_main": True}).status_code == 422

    hostname = _hostname()
    domain = _add(tenant2_owner, f"  HTTPS://{hostname.upper()}./bookings ")
    assert domain["hostname"] == hostname

    www = _add(tenant2_owner, f"www.{_hostname()}", is_main=False)
    assert www["include_www"] is False


# Redirect domains need a main domain, and a business has at most 4.
def test_redirect_domain_rules(tenant2_owner):
    response = tenant2_owner.post("/business/v1/domains", json={"hostname": _hostname(), "is_main": False})
    assert response.status_code == 400, response.text

    _add(tenant2_owner, _hostname())

    response = tenant2_owner.post("/business/v1/domains", json={"hostname": _hostname(), "is_main": True})
    assert response.status_code == 409, response.text

    for _ in range(4):
        _add(tenant2_owner, _hostname(), is_main=False)

    response = tenant2_owner.post("/business/v1/domains", json={"hostname": _hostname(), "is_main": False})
    assert response.status_code == 400, response.text


# A redirect domain sends visitors to the main domain once it's live. The
# business's certificate is replaced by one covering both, and the old one is
# only deleted after the new one is on the load balancer.
def test_redirect_domain_goes_live(tenant2_owner):
    main = _hostname()
    _make_live(tenant2_owner, main, include_www=False)
    [first] = FakeDomains.state.certificates

    other = _hostname()
    domain = _add(tenant2_owner, other, is_main=False, include_www=False)
    FakeDomains.publish(domain)

    _run_check()
    assert set(FakeDomains.state.certificates) - {first}, "a new certificate is requested"
    assert first in FakeDomains.state.routing["certificates"], "the old one keeps serving"

    FakeDomains.issue_all()
    _run_check()
    _run_check()

    assert _domain(tenant2_owner, other)["state"] == "active"
    assert first not in FakeDomains.state.certificates
    [current] = FakeDomains.state.certificates.values()
    assert current["hostnames"] == sorted([main, other])
    assert FakeDomains.state.routing["redirects"]["tenant2"] == {
        "hosts": sorted([f"tenant2.{settings.BASE_DOMAIN}", other]),
        "target": main,
    }


# Removing the main domain puts the site back on the generated host at
# once; its certificate and Google's authorizations go, then the domain.
# While redirect domains remain, the main domain can't be removed.
def test_removing_the_main_domain(tenant2_owner):
    hostname = _hostname()
    main = _make_live(tenant2_owner, hostname)
    redirect = _add(tenant2_owner, _hostname(), is_main=False)

    assert tenant2_owner.delete(f"/business/v1/domains/{main['id']}").status_code == 409

    assert tenant2_owner.delete(f"/business/v1/domains/{redirect['id']}").status_code == 200
    response = tenant2_owner.delete(f"/business/v1/domains/{main['id']}")
    assert response.status_code == 200, response.text
    assert response.json()["data"]["live_domain"] is None
    assert "tenant2" not in FakeDomains.state.routing["redirects"]
    assert _site_client(hostname).get("/location-branding/v1/public/business").status_code == 404

    _run_check()

    assert _listing(tenant2_owner)["domains"] == []
    assert FakeDomains.state.certificates == {}
    assert FakeDomains.state.authorizations == {}


# A domain whose records never appear is given up after 7 days.
def test_pending_domain_expires(api: Api, tenant2_owner):
    hostname = _hostname()
    _add(tenant2_owner, hostname)
    api.sql("UPDATE tenancy.tenant_domains SET created_at = now() - interval '8 days' WHERE hostname = :h", h=hostname)

    _run_check()

    expired = _domain(tenant2_owner, hostname)
    assert expired["state"] == "failed"
    assert "7 days" in expired["failure_reason"]


# A live domain whose records go missing is suspended after 3 daily checks
# in a row (the site goes back to the generated host), and comes back when
# they return.
def test_live_domain_suspended_and_restored(api: Api, tenant2_owner):
    hostname = _hostname()
    domain = _make_live(tenant2_owner, hostname)
    FakeDomains.unpublish(domain)

    def next_day():
        api.sql("UPDATE tenancy.tenant_domains SET last_checked_at = now() - interval '25 hours' WHERE hostname = :h", h=hostname)
        _run_check()

    next_day()
    next_day()
    assert _domain(tenant2_owner, hostname)["state"] == "active"

    next_day()
    assert _domain(tenant2_owner, hostname)["state"] == "suspended"
    assert _listing(tenant2_owner)["live_domain"] is None

    FakeDomains.publish(domain)
    next_day()
    assert _domain(tenant2_owner, hostname)["state"] == "active"
    assert _listing(tenant2_owner)["live_domain"] == hostname


# When Google can't issue the certificate, the domains waiting on it fail
# with Google's reason; the owner's Check now asks again.
def test_certificate_failure(tenant2_owner):
    hostname = _hostname()
    domain = _add(tenant2_owner, hostname)
    FakeDomains.publish(domain)

    _run_check()
    FakeDomains.issue_all(state="failed", reason="CAA record forbids issuing")
    _run_check()

    failed = _domain(tenant2_owner, hostname)
    assert failed["state"] == "failed"
    assert "CAA record forbids issuing" in failed["failure_reason"]


# Check now takes a domain as far as it can go at once.
def test_check_now(tenant2_owner):
    hostname = _hostname()
    domain = _add(tenant2_owner, hostname)
    FakeDomains.publish(domain)

    response = tenant2_owner.post("/business/v1/domains/check")
    assert response.status_code == 200, response.text
    assert response.json()["data"]["domains"][0]["state"] == "verified"

    FakeDomains.issue_all()

    response = tenant2_owner.post("/business/v1/domains/check")
    assert response.json()["data"]["domains"][0]["state"] == "active"
    assert response.json()["data"]["live_domain"] == hostname


# The scheduled check only answers on the platform's site with the secret.
def test_domain_check_needs_its_secret(monkeypatch):
    assert _check(secret="wrong").status_code == 404
    assert _check(host=f"tenant1.{settings.BASE_DOMAIN}").status_code == 404
    assert _check().status_code == 200

    monkeypatch.setattr(settings, "DOMAINS_CHECK_SECRET", None)
    assert _check().status_code == 404


# Only the owner sees and changes the business's domains.
def test_domains_are_the_owners(admin, tenant2_owner):
    assert admin.get("/business/v1/domains").status_code == 403

    domain = _add(tenant2_owner, _hostname())
    assert admin.delete(f"/business/v1/domains/{domain['id']}").status_code == 403


# In the database: an owner can add and remove domains but not move them
# along, or set the business's main domain.
def test_database_keeps_domain_states_to_the_check(api: Api, tenant2_owner):
    domain = _add(tenant2_owner, _hostname())
    [(owner_id,)] = api.sql("SELECT id FROM auth.users WHERE email = 'sa2user@test.com'")

    for statement in (
        "UPDATE tenancy.tenant_domains SET state = 'active' WHERE id = CAST(:id AS uuid)",
        "UPDATE tenancy.tenants SET custom_domain = 'stolen.example.com' WHERE code = 'tenant2'",
    ):
        with SessionLocal() as db:
            db.execute(text("SELECT set_config('app.user_id', :id, true)"), {"id": str(owner_id)})

            with pytest.raises(DBAPIError) as raised:
                db.execute(text(statement), {"id": domain["id"]})

            assert "Only the domain check" in str(raised.value)


# When the database loses track of a live domain (a dev rebuild wiped its
# rows), the check takes it off the load balancer and deletes our
# certificate and Google's authorization for it once they're an hour old.
# A younger one (a domain being added right now) and the platform's own
# base-domain are left alone.
def test_orphaned_google_resources_are_swept(api: Api, tenant2_owner):
    _make_live(tenant2_owner, _hostname(), include_www=False)

    state = FakeDomains.state
    [certificate] = list(state.certificates)
    [authorization] = list(state.authorizations)

    # The platform's own (created by the runbook), and one being added now.
    state.certificates["base-domain"] = {"hostnames": [], "authorizations": [], "state": "active", "reason": None}
    state.authorizations["base-domain"] = settings.BASE_DOMAIN
    state.authorizations["auth-being-added"] = "new.example.com.au"
    an_hour_and_more_ago = datetime.now(timezone.utc) - timedelta(hours=2)

    for name in (certificate, authorization, "base-domain"):
        state.created_at[name] = an_hour_and_more_ago

    state.created_at["auth-being-added"] = datetime.now(timezone.utc)

    # The rebuild: the database forgets the domain and its certificate.
    api.sql("DELETE FROM tenancy.tenant_domains")
    api.sql("DELETE FROM tenancy.tenant_certificates")
    api.sql("UPDATE tenancy.tenants SET custom_domain = NULL WHERE custom_domain IS NOT NULL")

    _run_check()

    assert state.routing["certificates"] == []
    assert certificate not in state.certificates
    assert authorization not in state.authorizations
    assert "base-domain" in state.certificates
    assert "base-domain" in state.authorizations
    assert "auth-being-added" in state.authorizations
