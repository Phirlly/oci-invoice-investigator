"""Validate explicit runtime inputs without implicit credential discovery."""

import re
from pathlib import Path


def runtime_settings(environment):
    def required(name):
        value = environment.get(name, "")
        if not value:
            raise ValueError(f"Missing runtime setting: {name}.")
        return value

    secret = required("WEB_SECRET_KEY")
    if len(secret) < 50:
        raise ValueError("WEB_SECRET_KEY must contain at least 50 characters.")
    host = required("WEB_HOST")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9.-]{0,251}[a-zA-Z0-9]", host):
        raise ValueError("WEB_HOST must be an explicit hostname without a scheme or wildcard.")
    port = required("DB_PORT")
    if not port.isdecimal() or not 1 <= int(port) <= 65535:
        raise ValueError("DB_PORT must be a valid port.")
    database = {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": required("DB_HOST"),
        "PORT": int(port),
        "NAME": required("DB_NAME"),
        "USER": required("DB_USER"),
        "PASSWORD": required("DB_PASSWORD"),
        "CONN_MAX_AGE": 0,
        "OPTIONS": {
            "connect_timeout": 5,
            "options": "-c statement_timeout=15000 -c lock_timeout=5000",
        },
    }
    static_root = required("WEB_STATIC_ROOT")
    if not Path(static_root).is_absolute():
        raise ValueError("WEB_STATIC_ROOT must be an absolute path.")
    return {
        "SECRET_KEY": secret,
        "ALLOWED_HOSTS": [host],
        "DATABASES": {"default": database},
        "STATIC_ROOT": static_root,
    }
