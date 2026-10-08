import re

from django.test import Client

from invoice_investigator.case_storage.models import FollowUpTask


def test_csrf_is_required_and_exact_confirmation_is_repeat_safe(sample_case):
    user, case, proposal = sample_case
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    url = f"/cases/{case.pk}/proposals/{proposal.pk}/"
    data = {"digest": proposal.digest, "confirm": "on"}
    assert client.post(url, data).status_code == 403
    response = client.get(url)
    token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.content.decode())[1]
    assert (
        client.post(url, {"digest": proposal.digest, "csrfmiddlewaretoken": token}).status_code
        == 400
    )
    data["csrfmiddlewaretoken"] = token
    first = client.post(url, data)
    second = client.post(url, data)
    assert first.status_code == second.status_code == 302
    assert first.url == second.url
    assert FollowUpTask.objects.count() == 1


def test_modified_digest_shows_conflict(sample_case, client):
    user, case, proposal = sample_case
    client.force_login(user)
    response = client.post(
        f"/cases/{case.pk}/proposals/{proposal.pk}/",
        {
            "digest": "0" * 64,
            "confirm": "on",
        },
    )
    assert response.status_code == 409
    assert not FollowUpTask.objects.exists()
