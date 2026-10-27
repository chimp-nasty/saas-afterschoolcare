"""
A location's services (created with the location) and their config (what
an admin sets: price, times, policies). Both are public, for the landing
page; only admins change the config.
"""

from contextlib import contextmanager
from datetime import timedelta

from tests.factories import Api


def _service(client, name: str) -> dict:
    services = client.get("/location-services/v1/").json()["data"]

    return next(s for s in services if s["service_name"] == name)


@contextmanager
def _restored_config(api: Api, service_id: str):
    """Put a service's config back after a test (every test shares it)."""
    [row] = api.sql(
        "SELECT is_active, current_price_cents, start_time, end_time, description, late_fee_cents, "
        "refund_cutoff_days, min_child_age, max_child_age, late_fee_grace_minutes, age_label, is_featured "
        "FROM public.location_service_config WHERE location_service_id = :id",
        id=service_id,
    )
    try:
        yield
    finally:
        api.sql(
            "UPDATE public.location_service_config SET is_active = :is_active, "
            "current_price_cents = :price, start_time = :start_time, end_time = :end_time, "
            "description = :description, late_fee_cents = :late_fee, "
            "refund_cutoff_days = :cutoff, min_child_age = :min_age, max_child_age = :max_age, "
            "late_fee_grace_minutes = :grace, age_label = :age_label, is_featured = :is_featured "
            "WHERE location_service_id = :id",
            age_label=row.age_label,
            is_featured=row.is_featured,
            is_active=row.is_active,
            price=row.current_price_cents,
            start_time=row.start_time,
            end_time=row.end_time,
            description=row.description,
            late_fee=row.late_fee_cents,
            cutoff=row.refund_cutoff_days,
            min_age=row.min_child_age,
            max_age=row.max_child_age,
            grace=row.late_fee_grace_minutes,
            id=service_id,
        )


# A customer can list the location's services (the dev seed offers all
# four), each with its times and policies.
def test_list_location_services(customer):
    response = customer.client.get("/location-services/v1/")

    assert response.status_code == 200
    services = response.json()["data"]
    assert len(services) == 4

    after_school = next(s for s in services if s["service_name"] == "After School Care")
    assert (after_school["start_time"], after_school["end_time"]) == ("15:00:00", "18:00:00")
    assert after_school["refund_cutoff_days"] == 2
    assert (after_school["min_child_age"], after_school["max_child_age"]) == (8, 17)


# Before login, the landing page can list a location's services.
def test_public_services_need_no_login(api: Api):
    response = api.client().get("/location-services/v1/public/location1")

    assert response.status_code == 200
    assert len(response.json()["data"]) == 4


# Another tenant's services never show, logged in or not.
def test_public_services_are_per_location(api: Api, tenant2_admin):
    tenant1 = {s["id"] for s in api.client().get("/location-services/v1/public/location1").json()["data"]}
    tenant2 = {s["id"] for s in tenant2_admin.get("/location-services/v1/").json()["data"]}

    assert tenant1.isdisjoint(tenant2)


# A new location gets every service type, each with a config from the type's
# defaults, not offered until an admin prices it.
def test_new_location_gets_its_services(api: Api):
    [(location_id,)] = api.sql(
        "INSERT INTO tenancy.locations (tenant_id, code, name, address_line_1, suburb, state, postcode) "
        "SELECT id, 'new-location', 'New location', '9 Test Street', 'Brisbane City', 'QLD', '4000' "
        "FROM tenancy.tenants WHERE code = 'tenant2' "
        "RETURNING id"
    )

    rows = api.sql(
        "SELECT st.code, lsc.is_active, lsc.current_price_cents, lsc.start_time = st.default_start_time "
        "FROM public.location_services ls "
        "JOIN public.service_types st ON st.id = ls.service_type_id "
        "JOIN public.location_service_config lsc ON lsc.location_service_id = ls.id "
        "WHERE ls.location_id = :location_id",
        location_id=location_id,
    )

    assert len(rows) == 4
    assert all(not is_active and price == 0 and default_times for _, is_active, price, default_times in rows)


# A superadmin can change a service's price, times, description and late fee;
# the list shows the change.
def test_superadmin_updates_service_config(api: Api, superadmin):
    service = _service(superadmin, "Weekend Care")

    with _restored_config(api, service["id"]):
        response = superadmin.patch(
            f"/location-services/v1/{service['id']}/config",
            json={
                "current_price_cents": 7500,
                "start_time": "09:00",
                "end_time": "16:00",
                "description": "  Sport and games  ",
                "late_fee_cents": 2500,
            },
        )

        assert response.status_code == 200, response.text
        updated = _service(superadmin, "Weekend Care")
        assert updated["current_price_cents"] == 7500
        assert (updated["start_time"], updated["end_time"]) == ("09:00:00", "16:00:00")
        assert updated["description"] == "Sport and games"
        assert updated["late_fee_cents"] == 2500


# A service can't be offered for $0, and can't end before it starts.
def test_service_config_rules(api: Api, superadmin):
    service = _service(superadmin, "Weekend Care")

    with _restored_config(api, service["id"]):
        response = superadmin.patch(
            f"/location-services/v1/{service['id']}/config",
            json={"current_price_cents": 0},
        )
        assert response.status_code == 400
        assert "price above $0" in response.json()["msg"]

        response = superadmin.patch(
            f"/location-services/v1/{service['id']}/config",
            json={"start_time": "17:00", "end_time": "09:00"},
        )
        assert response.status_code == 400
        assert "finish after it starts" in response.json()["msg"]

        response = superadmin.patch(
            f"/location-services/v1/{service['id']}/config",
            json={"min_child_age": 12, "max_child_age": 6},
        )
        assert response.status_code == 400
        assert "youngest age" in response.json()["msg"]


# A service that isn't offered disappears from the list and can't be booked.
def test_service_not_offered_cannot_be_booked(api: Api, superadmin, customer):
    service = _service(superadmin, "After School Care")
    child = api.new_child(customer)
    day = api.service_day()

    with _restored_config(api, service["id"]):
        superadmin.patch(f"/location-services/v1/{service['id']}/config", json={"is_active": False})

        assert service["id"] not in [s["id"] for s in superadmin.get("/location-services/v1/").json()["data"]]

        response = api.book(customer, {child["id"]: [day]})
        assert response.status_code == 400
        assert response.json()["msg"] == "This service isn't currently offered"


# Changing a service that doesn't exist (or is another location's) is 404.
def test_update_unknown_service_config(superadmin):
    response = superadmin.patch(
        "/location-services/v1/00000000-0000-0000-0000-000000000000/config",
        json={"current_price_cents": 7500},
    )

    assert response.status_code == 404


# A booking's review line carries its session times.
def test_booking_lines_have_session_times(api: Api, customer):
    child = api.new_child(customer)
    data = api.book(customer, {child["id"]: [api.service_day()]}).json()["data"]

    [line] = customer.client.get(f"/booking/v1/groups/{data['booking_group_id']}").json()["data"]["bookings"]

    assert (line["start_time"], line["end_time"]) == ("15:00:00", "18:00:00")


# The public location details include its address and contact details.
def test_public_location_has_its_address(api: Api):
    response = api.client().get("/location-branding/v1/public/location1")

    assert response.status_code == 200
    location = response.json()["data"]
    assert location["address_line_1"] == "1 Placeholder Street"
    assert (location["suburb"], location["state"], location["postcode"]) == ("Brisbane City", "QLD", "4000")
    assert location["latitude"] is None


# The tenant's landing page ("/") lists its centres, before login, and never
# another tenant's.
def test_public_locations_list_the_tenants_centres(api: Api):
    tenant1 = api.client().get("/location-branding/v1/public")
    tenant2 = api.client(tenant="tenant2").get("/location-branding/v1/public")

    assert tenant1.status_code == 200
    assert tenant2.status_code == 200, tenant2.text
    assert {loc["location_code"] for loc in tenant1.json()["data"]} >= {"location1", "location2"}
    assert {loc["tenant_code"] for loc in tenant2.json()["data"]} == {"tenant2"}


# The service days list returns every matching day rather than stopping at a
# default page size (more than 25 open days).
def test_list_service_days_is_not_capped(customer):
    response = customer.client.get(
        "/location-service-days/v1/",
        params={"is_open": True},
    )

    assert response.status_code == 200
    assert len(response.json()["data"]) > 25


# The superadmin's settings list every service, offered or not, so a service
# that's been switched off can be switched back on; families can't see it.
def test_superadmin_settings_list_every_service(api: Api, superadmin, customer):
    service = _service(superadmin, "Weekend Care")

    with _restored_config(api, service["id"]):
        superadmin.patch(f"/location-services/v1/{service['id']}/config", json={"is_active": False})

        settings = superadmin.get("/location-services/v1/settings").json()["data"]
        [weekend] = [s for s in settings if s["id"] == service["id"]]
        assert weekend["is_active"] is False

        response = superadmin.patch(f"/location-services/v1/{service['id']}/config", json={"is_active": True})
        assert response.status_code == 200, response.text
        assert response.json()["data"]["is_active"] is True

    assert customer.client.get("/location-services/v1/settings").status_code == 403


# Every setting a superadmin can change is saved: price, times, description,
# refund cutoff, ages and the late fee.
def test_superadmin_changes_every_setting(api: Api, superadmin):
    service = _service(superadmin, "Vacation Care")

    with _restored_config(api, service["id"]):
        response = superadmin.patch(
            f"/location-services/v1/{service['id']}/config",
            json={
                "current_price_cents": 7500,
                "start_time": "07:30:00",
                "end_time": "17:30:00",
                "description": "  Excursions most days  ",
                "refund_cutoff_days": 5,
                "min_child_age": 5,
                "max_child_age": 12,
                "late_fee_cents": 1500,
                "late_fee_grace_minutes": 10,
            },
        )
        assert response.status_code == 200, response.text

        data = response.json()["data"]
        assert (data["current_price_cents"], data["start_time"], data["end_time"]) == (7500, "07:30:00", "17:30:00")
        assert data["description"] == "Excursions most days"
        assert (data["refund_cutoff_days"], data["min_child_age"], data["max_child_age"]) == (5, 5, 12)
        assert (data["late_fee_cents"], data["late_fee_grace_minutes"]) == (1500, 10)


# A superadmin can give a service its own age wording (blank goes back to
# "Ages X–Y"), and feature one service: featuring another moves it.
def test_age_label_and_featured_service(api: Api, superadmin):
    after_school = _service(superadmin, "After School Care")
    weekend = _service(superadmin, "Weekend Care")

    with _restored_config(api, after_school["id"]), _restored_config(api, weekend["id"]):
        response = superadmin.patch(
            f"/location-services/v1/{after_school['id']}/config",
            json={"age_label": "  Years 7 to 12  ", "is_featured": True},
        )
        assert response.status_code == 200, response.text

        public = {s["id"]: s for s in api.client().get("/location-services/v1/public/location1").json()["data"]}
        assert public[after_school["id"]]["age_label"] == "Years 7 to 12"
        assert public[after_school["id"]]["is_featured"] is True

        superadmin.patch(f"/location-services/v1/{weekend['id']}/config", json={"is_featured": True})

        assert _service(superadmin, "Weekend Care")["is_featured"] is True
        assert _service(superadmin, "After School Care")["is_featured"] is False

        superadmin.patch(f"/location-services/v1/{after_school['id']}/config", json={"age_label": " "})

        assert _service(superadmin, "After School Care")["age_label"] is None


# The centre's page leads with the featured service, else the first offered,
# with its next open session that hasn't finished (closed and past days
# skipped) and the weekdays it runs over the next four weeks; nothing when
# the centre offers nothing.
def test_featured_service_and_next_session(api: Api):
    [(location_id, today)] = api.sql(
        "INSERT INTO tenancy.locations (tenant_id, code, name, address_line_1, suburb, state, postcode) "
        "SELECT id, 'featured-test', 'Featured test', '9 Test Street', 'Brisbane City', 'QLD', '4000' "
        "FROM tenancy.tenants WHERE code = 'tenant2' "
        "RETURNING id, (now() AT TIME ZONE timezone)::date"
    )
    client = api.client(tenant="tenant2")

    assert client.get("/location-services/v1/public/featured-test/featured").json()["data"] is None

    # After School Care only, 00:00 to 00:01: today's session has finished.
    [(service_id,)] = api.sql(
        "UPDATE public.location_service_config c "
        "SET is_active = TRUE, current_price_cents = 1000, start_time = '00:00', end_time = '00:01' "
        "FROM public.location_services ls JOIN public.service_types st ON st.id = ls.service_type_id "
        "WHERE ls.id = c.location_service_id AND ls.location_id = :location_id "
        "AND st.code = 'after_school_care' RETURNING c.location_service_id",
        location_id=location_id,
    )

    for offset, is_open in ((-1, True), (0, True), (1, False), (2, True), (3, True), (40, True)):
        api.sql(
            "INSERT INTO public.location_service_days "
            "(location_service_id, location_id, service_date, is_open, capacity, closed_reason) "
            "VALUES (:service_id, :location_id, CAST(:today AS date) + :offset, :is_open, 10, "
            "CASE WHEN :is_open THEN NULL ELSE 'Closed' END)",
            service_id=service_id,
            location_id=location_id,
            today=today,
            offset=offset,
            is_open=is_open,
        )

    featured = client.get("/location-services/v1/public/featured-test/featured").json()["data"]

    assert featured["location_service_id"] == str(service_id)
    assert featured["next_session_date"] == (today + timedelta(days=2)).isoformat()
    assert featured["weekdays"] == sorted(
        {(today + timedelta(days=offset)).isoweekday() for offset in (2, 3)}
    )


# Service settings are the business's: a centre admin can't see or change
# them, only a superadmin.
def test_admins_cannot_change_service_settings(api: Api, admin):
    service = _service(admin, "After School Care")

    assert admin.get("/location-services/v1/settings").status_code == 403
    assert admin.patch(f"/location-services/v1/{service['id']}/config", json={"description": "x"}).status_code == 403
