"""
LabAI Django Settings
Database: Supabase PostgreSQL via DATABASE_URL
Host:     Back4App Containers (port 8000)
"""
import os
import dj_database_url
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-change-this-in-back4app-env-vars-now"
)

DEBUG = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS_ENV = os.environ.get("ALLOWED_HOSTS", "*")
ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS_ENV.split(",")]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "labai.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "labai.wsgi.application"

# ── DATABASE ──────────────────────────────────────────────────────
# Back4App: set DATABASE_URL in Environment Variables
# Supabase URI format:
#   postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
#
# If DATABASE_URL is not set, falls back to local SQLite so app
# can at least start up and show error messages instead of crashing.

DATABASE_URL = os.environ.get("DATABASE_URL", "")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=60,
            conn_health_checks=True,
        )
    }
else:
    # Fallback — SQLite in /tmp (writable on Back4App, not persistent)
    # This lets the app START even without DATABASE_URL set.
    # Set DATABASE_URL in Back4App env vars to use Supabase.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": "/tmp/labai_fallback.db",
        }
    }

# ── STATIC FILES ──────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ── APP SETTINGS ──────────────────────────────────────────────────
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin@labai2024")

DATA_UPLOAD_MAX_MEMORY_SIZE = 200 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 200 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── SECURITY ──────────────────────────────────────────────────────
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER   = True
    X_FRAME_OPTIONS              = "DENY"
    SECURE_CONTENT_TYPE_NOSNIFF = True