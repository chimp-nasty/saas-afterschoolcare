"""
Child documents (schema/0004, docs/child-document-retention-policy.md): a
family uploads files straight to storage with a signed policy, the API
checks the stored file before accepting it, and accepting or removing one
sends the child back to medical review. Families add and remove documents;
staff only read them.
"""

from tests.factories import Api, FakeStorage


PDF = b"%PDF-1.7\n" + b"0" * 200
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 200


def _start(customer, child_id: str, content: bytes = PDF, **overrides):
    return customer.client.post(
        "/child-documents/v1/",
        json={
            "child_id": child_id,
            "document_type": "asthma_action_plan",
            "filename": "Asthma plan.pdf",
            "content_type": "application/pdf",
            "size_bytes": len(content),
            **overrides,
        },
    )


def _started(customer, child_id: str, content: bytes = PDF, **overrides) -> dict:
    response = _start(customer, child_id, content, **overrides)
    assert response.status_code == 201, response.text

    return response.json()["data"]


def _complete(customer, document_id: str):
    return customer.client.post(f"/child-documents/v1/{document_id}/complete")


def _uploaded(customer, child_id: str, content: bytes = PDF, **overrides) -> dict:
    """A document uploaded and accepted, the way the frontend does it."""
    started = _started(customer, child_id, content, **overrides)
    assert FakeStorage.receive(started["upload"], content)

    response = _complete(customer, started["document"]["id"])
    assert response.status_code == 200, response.text

    return response.json()["data"]


def _documents(client, child_id: str):
    return client.get("/child-documents/v1/", params={"child_id": child_id})


def _review_status(api: Api, child_id: str) -> str:
    [(status,)] = api.sql(
        "SELECT review_status::text FROM public.child_medical_state WHERE child_id = :id",
        id=child_id,
    )

    return status


def _approve(api: Api, child_id: str):
    api.sql(
        "UPDATE public.child_medical_state SET review_status = 'approved' WHERE child_id = :id",
        id=child_id,
    )


def _location(api: Api, tenant: str = "tenant1", location: str = "location1") -> tuple[str, str]:
    [(tenant_id, location_id)] = api.sql(
        "SELECT l.tenant_id::text, l.id::text FROM tenancy.locations l "
        "JOIN tenancy.tenants t ON t.id = l.tenant_id "
        "WHERE t.code = :tenant AND l.code = :location",
        tenant=tenant,
        location=location,
    )

    return tenant_id, location_id


# A family uploads a PDF: it goes to pending/ under their tenant, and once
# completed it's moved to the child's folder, listed with the stored size,
# and the pending copy is gone.
def test_family_uploads_a_document(api: Api, customer):
    child = api.new_child(customer)
    tenant_id, location_id = _location(api)

    started = _started(customer, child["id"])
    document_id = started["document"]["id"]

    assert started["document"]["upload_status"] == "pending"
    assert started["upload"]["fields"]["key"] == f"pending/tenants/{tenant_id}/{document_id}"
    assert FakeStorage.state.uploads[started["upload"]["fields"]["key"]]["metadata"] == {
        "tenant-id": tenant_id,
        "location-id": location_id,
        "child-id": child["id"],
        "document-id": document_id,
    }

    assert FakeStorage.receive(started["upload"], PDF)

    response = _complete(customer, document_id)
    assert response.status_code == 200, response.text

    document = response.json()["data"]
    assert document["upload_status"] == "uploaded"
    assert document["size_bytes"] == len(PDF)
    assert document["filename"] == "Asthma plan.pdf"

    final_key = f"documents/tenants/{tenant_id}/locations/{location_id}/children/{child['id']}/{document_id}"
    assert FakeStorage.keys() == {final_key}

    response = _documents(customer.client, child["id"])
    assert response.status_code == 200, response.text
    assert [d["id"] for d in response.json()["data"]] == [document_id]


# A document counts as medical details: accepting one sends even a child
# with no medical text (not_required) to review.
def test_uploading_a_document_needs_medical_review(api: Api, customer):
    child = api.new_child(customer)
    assert _review_status(api, child["id"]) == "not_required"

    _uploaded(customer, child["id"])

    assert _review_status(api, child["id"]) == "pending"


# An approved child goes back to review when the family uploads another
# document.
def test_uploading_to_an_approved_child_needs_review_again(api: Api, customer):
    child = api.new_child(customer, medical_info="Asthma")
    _approve(api, child["id"])

    _uploaded(customer, child["id"])

    assert _review_status(api, child["id"]) == "pending"


# An upload that never finishes doesn't count: it isn't listed and the
# child's review doesn't change.
def test_unfinished_upload_is_not_listed(api: Api, customer):
    child = api.new_child(customer)

    _started(customer, child["id"])

    assert _documents(customer.client, child["id"]).json()["data"] == []
    assert _review_status(api, child["id"]) == "not_required"


# Completing before the file has arrived is refused, but the upload stays
# open: the family can upload and complete again.
def test_complete_before_the_file_arrives(api: Api, customer):
    child = api.new_child(customer)
    started = _started(customer, child["id"])
    document_id = started["document"]["id"]

    response = _complete(customer, document_id)
    assert response.status_code == 400, response.text

    assert FakeStorage.receive(started["upload"], PDF)

    response = _complete(customer, document_id)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["upload_status"] == "uploaded"


# Completing twice (e.g. a retry after a lost response) returns the same
# accepted document.
def test_complete_is_repeatable(api: Api, customer):
    child = api.new_child(customer)
    document = _uploaded(customer, child["id"])

    response = _complete(customer, document["id"])
    assert response.status_code == 200, response.text
    assert response.json()["data"]["id"] == document["id"]


# A file that isn't what it claims (an HTML page sent as a PDF) is
# rejected after upload: deleted from storage, marked failed, never listed,
# and it can't be completed again.
def test_file_that_is_not_its_declared_type_is_rejected(api: Api, customer):
    child = api.new_child(customer)
    content = b"<html><script>alert(1)</script></html>"
    started = _started(customer, child["id"], content)
    document_id = started["document"]["id"]

    assert FakeStorage.receive(started["upload"], content)

    response = _complete(customer, document_id)
    assert response.status_code == 400, response.text

    assert FakeStorage.keys() == set()
    assert _documents(customer.client, child["id"]).json()["data"] == []
    assert _review_status(api, child["id"]) == "not_required"

    [(status,)] = api.sql(
        "SELECT upload_status::text FROM public.child_documents WHERE id = :id",
        id=document_id,
    )
    assert status == "failed"

    response = _complete(customer, document_id)
    assert response.status_code == 409, response.text


# A photo is accepted as an image of its own type.
def test_family_uploads_a_photo(api: Api, customer):
    child = api.new_child(customer)

    document = _uploaded(customer, child["id"], PNG, filename="plan.png", content_type="image/png")

    assert document["content_type"] == "image/png"


# Only PDFs and photos are accepted, and nothing over 10 MB: refused before
# anything is signed.
def test_unsupported_type_and_oversized_files_are_refused(api: Api, customer):
    child = api.new_child(customer)

    response = _start(customer, child["id"], content_type="text/html")
    assert response.status_code == 400, response.text

    response = _start(customer, child["id"], size_bytes=10 * 1024 * 1024 + 1)
    assert response.status_code == 400, response.text

    assert FakeStorage.state.uploads == {}


# The signed upload itself caps the size, so a browser can't send more
# than 10 MB whatever it declared.
def test_upload_policy_caps_the_size(api: Api, customer):
    child = api.new_child(customer)
    started = _started(customer, child["id"])

    assert not FakeStorage.receive(started["upload"], b"%PDF-" + b"0" * (10 * 1024 * 1024))


# Staff can see a child's documents and get a short-lived link to view one;
# every link is issued for the type we checked.
def test_staff_can_view_documents(api: Api, customer, admin):
    child = api.new_child(customer)
    document = _uploaded(customer, child["id"])

    response = _documents(admin, child["id"])
    assert response.status_code == 200, response.text
    assert [d["id"] for d in response.json()["data"]] == [document["id"]]

    response = admin.get(f"/child-documents/v1/{document['id']}/download")
    assert response.status_code == 200, response.text
    assert response.json()["data"]["url"].startswith("https://storage.test/")
    assert FakeStorage.state.download_links[-1]["content_type"] == "application/pdf"


# The family can view their own documents too.
def test_family_can_view_their_document(api: Api, customer):
    child = api.new_child(customer)
    document = _uploaded(customer, child["id"])

    response = customer.client.get(f"/child-documents/v1/{document['id']}/download")
    assert response.status_code == 200, response.text


# Staff read documents but don't add or remove them: those are the
# family's records.
def test_staff_cannot_add_or_remove_documents(api: Api, customer, admin):
    child = api.new_child(customer)
    document = _uploaded(customer, child["id"])

    response = admin.post(
        "/child-documents/v1/",
        json={
            "child_id": child["id"],
            "document_type": "other",
            "filename": "x.pdf",
            "content_type": "application/pdf",
            "size_bytes": 10,
        },
    )
    assert response.status_code == 403, response.text

    response = admin.post(f"/child-documents/v1/{document['id']}/remove")
    assert response.status_code == 403, response.text


# Another family can't see, view, upload to or remove a child's documents:
# to them the child and document don't exist.
def test_other_family_cannot_reach_documents(api: Api, customer, other_customer):
    child = api.new_child(customer)
    document = _uploaded(customer, child["id"])

    assert _documents(other_customer.client, child["id"]).status_code == 404
    assert other_customer.client.get(f"/child-documents/v1/{document['id']}/download").status_code == 404
    assert _start(other_customer, child["id"]).status_code == 404
    assert other_customer.client.post(f"/child-documents/v1/{document['id']}/remove").status_code == 404


# Staff at another tenant can't reach a child's documents.
def test_other_tenant_cannot_reach_documents(api: Api, customer, tenant2_admin):
    child = api.new_child(customer)
    document = _uploaded(customer, child["id"])

    assert _documents(tenant2_admin, child["id"]).status_code == 404
    assert tenant2_admin.get(f"/child-documents/v1/{document['id']}/download").status_code == 404


# A link is only signed for the document's own key, under its child's
# tenant and location; a row pointing anywhere else gets nothing.
def test_no_link_for_a_key_outside_the_childs_folder(api: Api, customer):
    child = api.new_child(customer)
    other_child = api.new_child(api.new_customer())
    document = _uploaded(customer, child["id"])

    tenant_id, location_id = _location(api)
    api.sql(
        "UPDATE public.child_documents SET storage_object_key = :key WHERE id = :id",
        key=f"documents/tenants/{tenant_id}/locations/{location_id}/children/{other_child['id']}/{document['id']}",
        id=document["id"],
    )

    response = customer.client.get(f"/child-documents/v1/{document['id']}/download")
    assert response.status_code == 404, response.text
    assert FakeStorage.state.download_links == []


# Removing a document hides it, keeps the file (retention), and sends the
# child back to review.
def test_family_removes_a_document(api: Api, customer):
    child = api.new_child(customer)
    document = _uploaded(customer, child["id"])
    _approve(api, child["id"])
    keys_before = FakeStorage.keys()

    response = customer.client.post(f"/child-documents/v1/{document['id']}/remove")
    assert response.status_code == 200, response.text
    assert response.json()["data"]["is_active"] is False

    assert _documents(customer.client, child["id"]).json()["data"] == []
    assert FakeStorage.keys() == keys_before
    assert _review_status(api, child["id"]) == "pending"

    response = customer.client.post(f"/child-documents/v1/{document['id']}/remove")
    assert response.status_code == 404, response.text


# A removed document can't be viewed any more.
def test_removed_document_cannot_be_viewed(api: Api, customer):
    child = api.new_child(customer)
    document = _uploaded(customer, child["id"])
    customer.client.post(f"/child-documents/v1/{document['id']}/remove")

    response = customer.client.get(f"/child-documents/v1/{document['id']}/download")
    assert response.status_code == 404, response.text


# Documents can't be added to a child the family has removed.
def test_no_documents_for_a_removed_child(api: Api, customer):
    child = api.new_child(customer)

    response = customer.client.post(f"/children/v1/{child['id']}/deactivate")
    assert response.status_code == 200, response.text

    response = _start(customer, child["id"])
    assert response.status_code == 409, response.text
    assert FakeStorage.state.uploads == {}
