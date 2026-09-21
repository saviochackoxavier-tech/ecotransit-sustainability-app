"""
Django settings for the EcoTransit project.

Phase 1 scope only: project foundation, environment-driven configuration,
database (SQLite dev / PostgreSQL-ready), static & media file configuration,
and baseline security defaults.

No EcoTransit domain apps, models, or API endpoints are configured here —
those belong to later phases per the v2.1.1 specification.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/
"""

from pathlib import Path

import dj_database_url
from decouple import Csv, config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# -----------------------------------------------------------------------
# Core / security
# -----------------------------------------------------------------------
# SECURITY WARNING: keep the secret key used in production secret!
# Falls back to an obviously-fake local-only value so `manage.py check` and
# local development work even if .env hasn't been created yet, but any real
# deployment MUST set DJANGO_SECRET_KEY via the environment.
SECRET_KEY = config(
    "DJANGO_SECRET_KEY",
    default="django-insecure-local-dev-only-do-not-use-in-production",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DJANGO_DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())


# -----------------------------------------------------------------------
# Application definition
# -----------------------------------------------------------------------
# Phase 1 shipped only Django's built-in apps. Phase 2 adds `core`, which
# holds the EcoTransit domain models only (no views/APIs yet — see
# core/models.py and README.md for phase boundaries).
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ecotransit.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "ecotransit.wsgi.application"
ASGI_APPLICATION = "ecotransit.asgi.application"


# -----------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------
# Spec (Section 2): "SQLite (local development), PostgreSQL-ready
# (DATABASE_URL via dj-database-url)".
#
# If DATABASE_URL is set in the environment, it is used (e.g. for
# PostgreSQL). Otherwise, local development falls back to SQLite with no
# extra setup required.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}


# -----------------------------------------------------------------------
# Password validation
# -----------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# -----------------------------------------------------------------------
# Internationalization
# -----------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# -----------------------------------------------------------------------
# Static & media files
# -----------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# -----------------------------------------------------------------------
# Security (production-oriented, environment-driven, dev-safe defaults)
# -----------------------------------------------------------------------
# These are all no-ops / safe under local DEBUG=True and only take effect
# when DEBUG=False (production), or can be explicitly overridden via env.
SECURE_SSL_REDIRECT = config("DJANGO_SECURE_SSL_REDIRECT", default=not DEBUG, cast=bool)
SESSION_COOKIE_SECURE = config("DJANGO_SESSION_COOKIE_SECURE", default=not DEBUG, cast=bool)
CSRF_COOKIE_SECURE = config("DJANGO_CSRF_COOKIE_SECURE", default=not DEBUG, cast=bool)

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Note (Phase 6 polish): SECURE_BROWSER_XSS_FILTER (and the X-XSS-Protection
# header it controlled) was deprecated in Django 3.0 and removed in Django
# 4.0, since modern browsers dropped support for that header in favor of
# CSP. Setting it on Django 5.x is a silent no-op, so it's intentionally
# left out here rather than kept as dead configuration.

# CSRF_COOKIE_HTTPONLY is left at its default (False) intentionally: the
# frontend's tracking.js reads the csrftoken cookie directly via
# document.cookie to attach it to its own fetch() calls (see
# core/static/core/js/tracking.js). Setting this True would break that
# without adding meaningful protection here, since Django's CSRF design
# already relies on the token being readable by same-origin JS.

SECURE_HSTS_SECONDS = config("DJANGO_SECURE_HSTS_SECONDS", default=0 if DEBUG else 31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

CSRF_TRUSTED_ORIGINS = config("DJANGO_CSRF_TRUSTED_ORIGINS", default="", cast=Csv())

# -----------------------------------------------------------------------
# Auth (Phase 5): minimal login/logout wiring for the HTML frontend.
# No password-reset flow is wired in — that requires a configured email
# backend, which is out of scope for this phase.
# -----------------------------------------------------------------------
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"


# -----------------------------------------------------------------------
# Third-party service configuration (Phase 3)
# -----------------------------------------------------------------------
# OpenRouteService — routing/geocoding wrapper lives in core/services/.
# No default base URL override is normally needed; OPENROUTESERVICE_BASE_URL
# exists mainly to allow pointing at a mock/test server if ever needed.
OPENROUTESERVICE_API_KEY = config("OPENROUTESERVICE_API_KEY", default="")
OPENROUTESERVICE_BASE_URL = config(
    "OPENROUTESERVICE_BASE_URL", default="https://api.openrouteservice.org"
)
