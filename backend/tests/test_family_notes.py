"""
Notes and messages (Admin › Families, slice 4-5). Admins and superadmins
write notes about a family's children: staff-only, read at the staff kiosk
too, never shown to the family, and fixed once saved. They also send the
family messages, which the family reads in their account; the email only
says there's one. A message can be withdrawn until it's read.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from app.integrations.email.messages import NewMessageEmail
from tests.factories import Api, StaffMember


BASE = "/families/v1"
KIOSK = "/staff-kiosk/v1/location1"


def _family_id(api: Api, customer) -> str:
    [(user_id,)] = api.sql("SELECT id::text FROM auth.users WHERE email = :e", e=customer.email)

    return user_id


def _add_note(client, user_id: str, child_id: str, note: str = "Prefers to be called Billy."):
    return client.post(f"{BASE}/{user_id}/notes", json={"child_id": child_id, "note": note})


def _send(client, user_id: str, **body):
    return client.post(f"{BASE}/{user_id}/messages", json={"title": "Pickup times", "message": "Pickup closes at 6pm.", **body})


def _session_as(api: Api, user_id: str):
    """A database session as this user at tenant1/location1 on the website."""
    [(location_id,)] = api.sql(
        "SELECT l.id::text FROM tenancy.locations l JOIN tenancy.tenants t ON t.id = l.tenant_id "
        "WHERE t.code = 'tenant1' AND l.code = 'location1'"
    )
    db = SessionLocal()
    db.execute(
        text("SELECT set_config('app.user_id', :u, true), set_config('app.location_id', :l, true)"),
        {"u": user_id, "l": location_id},
    )

    return db


@pytest.fixture
def staff_tablet(api: Api, admin):
    return api.kiosk(admin, "staff")


@pytest.fixture
def on_shift(api: Api, staff_tablet) -> StaffMember:
    """A staff member clocked in at the staff kiosk."""
    member = api.new_staff()
    response = staff_tablet.post(
        f"{KIOSK}/shift",
        json={"action": "start"},
        headers={"X-Kiosk-Staff": member.user_id, "X-Kiosk-Pin": member.pin},
    )
    assert response.status_code == 200, response.text

    return member


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


# An admin adds a note about a child; the family's notes list it, newest
# first, with the child's name and who wrote it as "Sam L.".
def test_add_and_list_notes(api: Api, admin, customer):
    user_id = _family_id(api, customer)
    child = api.new_child(customer, first_name="Wilhelmina")

    assert _add_note(admin, user_id, child["id"], "First note").status_code == 201
    response = _add_note(admin, user_id, child["id"], "  Second note  ")
    assert response.status_code == 201, response.text
    assert response.json()["data"]["note"] == "Second note"

    notes = admin.get(f"{BASE}/{user_id}/notes").json()["data"]
    assert [n["note"] for n in notes] == ["Second note", "First note"]
    assert notes[0]["child_first_name"] == "Wilhelmina"
    assert notes[0]["created_by"]


# A superadmin can add and delete notes too.
def test_superadmin_notes(api: Api, superadmin, customer):
    user_id = _family_id(api, customer)
    child = api.new_child(customer)

    note = _add_note(superadmin, user_id, child["id"]).json()["data"]

    assert superadmin.delete(f"{BASE}/{user_id}/notes/{note['id']}").status_code == 200
    assert superadmin.get(f"{BASE}/{user_id}/notes").json()["data"] == []


# A note must say something, and must be about one of this family's
# children: another family's child isn't found.
def test_note_needs_text_and_the_familys_child(api: Api, admin, customer):
    user_id = _family_id(api, customer)
    child = api.new_child(customer)
    other = api.new_customer()
    other_child = api.new_child(other)

    assert _add_note(admin, user_id, child["id"], "   ").status_code == 422
    assert _add_note(admin, user_id, other_child["id"]).status_code == 404


# An admin deletes a note; deleting it again, or through another family,
# finds nothing.
def test_delete_note(api: Api, admin, customer):
    user_id = _family_id(api, customer)
    child = api.new_child(customer)
    other_id = _family_id(api, api.new_customer())
    note = _add_note(admin, user_id, child["id"]).json()["data"]

    assert admin.delete(f"{BASE}/{other_id}/notes/{note['id']}").status_code == 404
    assert admin.delete(f"{BASE}/{user_id}/notes/{note['id']}").status_code == 200
    assert admin.delete(f"{BASE}/{user_id}/notes/{note['id']}").status_code == 404


# A saved note can't be changed, even directly in the database by an admin
# session: it's deleted and written again.
def test_notes_are_fixed(api: Api, admin, customer):
    user_id = _family_id(api, customer)
    child = api.new_child(customer)
    note = _add_note(admin, user_id, child["id"]).json()["data"]
    [(admin_id,)] = api.sql("SELECT id::text FROM auth.users WHERE email = 't1user@test.com'")

    with _session_as(api, admin_id) as db:
        with pytest.raises(IntegrityError, match="changed once saved"):
            db.execute(text("UPDATE public.child_notes SET note = 'Changed' WHERE id = :id"), {"id": note["id"]})


# Families never see notes, not even through the database: RLS hides them
# from the family's own session. They can't reach the notes routes either.
def test_family_never_sees_notes(api: Api, admin, customer):
    user_id = _family_id(api, customer)
    child = api.new_child(customer)
    _add_note(admin, user_id, child["id"])

    with _session_as(api, user_id) as db:
        count = db.execute(text("SELECT count(*) FROM public.child_notes WHERE child_id = :c"), {"c": child["id"]}).scalar()

    assert count == 0
    assert customer.client.get(f"{BASE}/{user_id}/notes").status_code == 403
    assert _add_note(customer.client, user_id, child["id"]).status_code == 403


# Staff can't read or write notes on the website (no child data there).
def test_staff_cannot_use_notes_on_the_website(api: Api, admin, customer):
    user_id = _family_id(api, customer)
    child = api.new_child(customer)
    staff = api.new_staff(pin=None)

    assert staff.client.get(f"{BASE}/{user_id}/notes").status_code == 403
    assert _add_note(staff.client, user_id, child["id"]).status_code == 403


# At the staff kiosk, staff on shift read a child's notes with a PIN, and
# the run sheet marks children who have notes. Without a PIN, no notes.
def test_staff_read_notes_at_the_kiosk(api: Api, admin, staff_tablet, on_shift, customer):
    user_id = _family_id(api, customer)
    child = api.new_child(customer)
    api.booking_today(customer, child["id"])
    _add_note(admin, user_id, child["id"], "Collected by Gran on Fridays.")
    headers = {"X-Kiosk-Staff": on_shift.user_id, "X-Kiosk-Pin": on_shift.pin}

    assert staff_tablet.get(f"{KIOSK}/children/{child['id']}/notes").status_code == 401

    response = staff_tablet.get(f"{KIOSK}/children/{child['id']}/notes", headers=headers)
    assert response.status_code == 200, response.text
    assert [n["note"] for n in response.json()["data"]] == ["Collected by Gran on Fridays."]

    board = staff_tablet.get(f"{KIOSK}/board").json()["data"]
    [row] = [e for e in board["entries"] if e["child_id"] == child["id"]]
    assert row["has_notes"] is True


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


# An admin sends a plain message (no link): the family sees it in their
# account, and is emailed only that there's a message, never its text.
def test_send_plain_message(api: Api, admin, customer, sent_emails):
    user_id = _family_id(api, customer)

    response = _send(admin, user_id, message="Pickup closes at 6pm from Monday.")
    assert response.status_code == 201, response.text
    assert response.json()["data"]["target"] is None

    [action] = customer.client.get("/action/v1/").json()["data"]
    assert (action["title"], action["message"], action["target"]) == ("Pickup times", "Pickup closes at 6pm from Monday.", None)

    [email] = sent_emails(NewMessageEmail)
    assert email.to_email == customer.email
    assert "6pm" not in repr(email)


# A message about a child can link to one of that child's pages; the
# admin's list shows the child and whether the family has read it.
def test_message_about_a_child(api: Api, admin, customer):
    user_id = _family_id(api, customer)
    child = api.new_child(customer, first_name="Wilhelmina")

    response = _send(admin, user_id, child_id=child["id"], target="manage-documents")
    assert response.status_code == 201, response.text

    [message] = admin.get(f"{BASE}/{user_id}/messages").json()["data"]
    assert (message["child_first_name"], message["target"], message["cited_at"]) == ("Wilhelmina", "manage-documents", None)
    assert message["created_by"]

    customer.client.patch(f"/action/v1/{message['id']}")

    [message] = admin.get(f"{BASE}/{user_id}/messages").json()["data"]
    assert message["cited_at"] is not None


# A link must fit the message: a child's page needs a child, an account
# page can't be about a child; the child must be the family's own.
def test_message_link_must_fit(api: Api, admin, customer):
    user_id = _family_id(api, customer)
    child = api.new_child(customer)
    other_child = api.new_child(api.new_customer())

    assert _send(admin, user_id, target="manage-documents").status_code == 422
    assert _send(admin, user_id, child_id=child["id"], target="pickups").status_code == 422
    assert _send(admin, user_id, child_id=other_child["id"]).status_code == 404
    assert _send(admin, user_id, title=" ").status_code == 422


# An unread message can be withdrawn; once the family has read it, it can't.
def test_withdraw_until_read(api: Api, admin, customer):
    user_id = _family_id(api, customer)
    unread = _send(admin, user_id).json()["data"]
    read = _send(admin, user_id, title="Read this").json()["data"]
    customer.client.patch(f"/action/v1/{read['id']}")

    assert admin.delete(f"{BASE}/{user_id}/messages/{unread['id']}").status_code == 200
    assert admin.delete(f"{BASE}/{user_id}/messages/{read['id']}").status_code == 409
    assert [m["id"] for m in admin.get(f"{BASE}/{user_id}/messages").json()["data"]] == [read["id"]]


# A superadmin can send and withdraw messages too; families and staff can't.
def test_who_can_send_messages(api: Api, superadmin, customer):
    user_id = _family_id(api, customer)
    staff = api.new_staff(pin=None)

    message = _send(superadmin, user_id).json()["data"]
    assert superadmin.delete(f"{BASE}/{user_id}/messages/{message['id']}").status_code == 200

    assert _send(customer.client, user_id).status_code == 403
    assert _send(staff.client, user_id).status_code == 403
    assert staff.client.get(f"{BASE}/{user_id}/messages").status_code == 403
