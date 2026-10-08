"""Pure common settings shared by explicit test and runtime configuration."""

from datetime import timedelta


def common_settings():
    return {
        "DEBUG": False,
        "INSTALLED_APPS": [
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.staticfiles",
            "axes",
            "invoice_investigator.case_storage",
            "invoice_investigator.web",
        ],
        "MIDDLEWARE": [
            "django.middleware.security.SecurityMiddleware",
            "invoice_investigator.web.middleware.ResponsePolicy",
            "whitenoise.middleware.WhiteNoiseMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.middleware.clickjacking.XFrameOptionsMiddleware",
            "axes.middleware.AxesMiddleware",
        ],
        "ROOT_URLCONF": "invoice_investigator.web.urls",
        "TEMPLATES": [
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "APP_DIRS": True,
                "OPTIONS": {
                    "context_processors": [
                        "django.template.context_processors.request",
                        "django.contrib.auth.context_processors.auth",
                    ]
                },
            }
        ],
        "AUTHENTICATION_BACKENDS": [
            "axes.backends.AxesStandaloneBackend",
            "django.contrib.auth.backends.ModelBackend",
        ],
        "AUTH_PASSWORD_VALIDATORS": [
            {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
            {
                "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
                "OPTIONS": {"min_length": 12},
            },
            {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
            {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
        ],
        "DEFAULT_AUTO_FIELD": "django.db.models.BigAutoField",
        "USE_TZ": True,
        "TIME_ZONE": "UTC",
        "STATIC_URL": "/static/",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SECURE": True,
        "CSRF_COOKIE_SECURE": True,
        "SECURE_SSL_REDIRECT": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_AGE": 3600,
        "CSRF_COOKIE_HTTPONLY": True,
        "CSRF_COOKIE_SAMESITE": "Lax",
        "SECURE_CONTENT_TYPE_NOSNIFF": True,
        "SECURE_REFERRER_POLICY": "same-origin",
        "X_FRAME_OPTIONS": "DENY",
        "DATA_UPLOAD_MAX_MEMORY_SIZE": 32_768,
        "LOGIN_URL": "/sign-in/",
        "LOGIN_REDIRECT_URL": "/",
        "LOGOUT_REDIRECT_URL": "/sign-in/",
        "AXES_HANDLER": "invoice_investigator.web.login_attempts.PrivateLoginAttempts",
        "AXES_FAILURE_LIMIT": 5,
        "AXES_COOLOFF_TIME": timedelta(minutes=15),
        "AXES_LOCKOUT_PARAMETERS": ["username"],
        "AXES_RESET_ON_SUCCESS": True,
        "AXES_VERBOSE": False,
        "AXES_DISABLE_ACCESS_LOG": True,
        "AXES_IPWARE_META_PRECEDENCE_ORDER": ("REMOTE_ADDR",),
        "AXES_LOCKOUT_TEMPLATE": "review/login_locked.html",
    }
