from axes.models import AccessAttempt
from django.test import Client


def test_login_rotates_session_and_logout_requires_post(sample_case):
    _, _, _ = sample_case
    client = Client()
    session = client.session
    session["pre_login_marker"] = "synthetic"
    session.save()
    before_login = session.session_key
    response = client.post("/sign-in/", {"username": "reviewer", "password": "local-test-password"})
    assert response.status_code == 302
    assert client.session.session_key != before_login
    assert client.get("/").status_code == 200
    assert client.get("/sign-out/").status_code == 405
    assert client.post("/sign-out/").status_code == 302
    assert client.get("/").status_code == 302


def test_lockout_survives_new_cookies_user_agents_and_forwarded_ip(sample_case):
    for index in range(5):
        response = Client().post(
            "/sign-in/",
            {"username": "reviewer", "password": "wrong"},
            HTTP_USER_AGENT=f"changed-{index}",
            HTTP_X_FORWARDED_FOR=f"203.0.113.{index}",
        )
    assert response.status_code == 429

    response = Client().post(
        "/sign-in/",
        {
            "username": "reviewer",
            "password": "local-test-password",
        },
        HTTP_USER_AGENT="another-browser",
        HTTP_X_FORWARDED_FOR="198.51.100.9",
    )
    assert response.status_code == 429


def test_failed_login_does_not_persist_request_bodies(sample_case):
    Client().post(
        "/sign-in/?private_payload=synthetic-private-marker",
        {
            "username": "reviewer",
            "password": "wrong",
            "customer_document": "synthetic-private-marker",
        },
    )
    attempt = AccessAttempt.objects.get()
    assert attempt.get_data == ""
    assert attempt.post_data == ""
