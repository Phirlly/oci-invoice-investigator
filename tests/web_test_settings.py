"""Pure test configuration; database credentials are loaded only by runtime fixture."""

from invoice_investigator.web.configuration import common_settings

globals().update(common_settings())
SECRET_KEY = "public-test-only-signing-value-not-a-deployment-secret"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": "127.0.0.1",
        "PORT": 0,
        "NAME": "invoice_checks",
        "USER": "invoice_checks",
        "PASSWORD": "",
        "CONN_MAX_AGE": 0,
        "OPTIONS": {
            "connect_timeout": 3,
            "options": "-c statement_timeout=5000 -c lock_timeout=4000",
        },
    }
}
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.PBKDF2PasswordHasher"]
