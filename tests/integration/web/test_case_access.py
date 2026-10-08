import pytest

from invoice_investigator.case_storage.models import FollowUpTask

ROUTES = [
    "/cases/case-001/",
    "/cases/case-001/revisions/1/evidence/invoice.pdf/",
    "/cases/case-001/revisions/1/records/purchasing.json/",
]


@pytest.mark.parametrize("route", ROUTES)
def test_other_case_with_same_po_remains_private(sample_case, client, route):
    user, _, _ = sample_case
    client.force_login(user)
    response = client.get(route)
    assert response.status_code == 404
    assert b"INV-1001" not in response.content


def test_authorized_evidence_and_exact_register_record(sample_case, client):
    user, _, _ = sample_case
    client.force_login(user)
    pdf = client.get("/cases/case-002/revisions/1/evidence/invoice.pdf/")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
    assert pdf["Cache-Control"] == "private, no-store"
    record = client.get("/cases/case-002/revisions/1/records/purchasing.json/?pointer=/receipts/0")
    assert record.status_code == 200
    assert b"80" in record.content
    assert (
        client.get("/cases/case-002/revisions/1/records/purchasing.json/?pointer=/bad").status_code
        == 404
    )


def test_get_confirmation_never_creates_task(sample_case, client):
    user, case, proposal = sample_case
    client.force_login(user)
    response = client.get(f"/cases/{case.pk}/proposals/{proposal.pk}/")
    assert response.status_code == 200
    assert b"physical nondelivery is not established" in response.content
    assert not FollowUpTask.objects.exists()


def test_anonymous_case_redirects_to_sign_in(sample_case, client):
    response = client.get("/cases/case-002/")
    assert response.status_code == 302
    assert response.url.startswith("/sign-in/")
