import pytest

from invoice_investigator.web.configuration import common_settings
from invoice_investigator.web.runtime_configuration import runtime_settings


def test_common_settings_require_https_and_do_not_trust_forwarded_headers():
    settings = common_settings()
    assert settings["SESSION_COOKIE_SECURE"]
    assert settings["CSRF_COOKIE_SECURE"]
    assert settings["SECURE_SSL_REDIRECT"]
    assert "SECURE_PROXY_SSL_HEADER" not in settings


def test_runtime_rejects_missing_deployment_settings():
    with pytest.raises(ValueError, match="WEB_SECRET_KEY"):
        runtime_settings({})


def test_runtime_uses_only_explicit_host_and_database_settings():
    settings = runtime_settings(
        {
            "WEB_SECRET_KEY": "example-only-value-" * 4,
            "WEB_HOST": "demo.example.invalid",
            "DB_HOST": "database",
            "DB_PORT": "5432",
            "DB_NAME": "invoice_app",
            "DB_USER": "invoice_app",
            "DB_PASSWORD": "example-only-password",
            "WEB_STATIC_ROOT": "/app/static",
        }
    )
    assert settings["ALLOWED_HOSTS"] == ["demo.example.invalid"]
    assert settings["DATABASES"]["default"]["ENGINE"] == "django.db.backends.postgresql"
    assert settings["DATABASES"]["default"]["PORT"] == 5432
