"""
LabAI Django Settings
Database: Supabase PostgreSQL via DATABASE_URL
Host:     Back4App Containers
"""
import os
import dj_database_url
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-change-this-in-back4app-env-vars"
)

DEBUG = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS = ["*"]  # Back4App handles SSL termination

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
# Set DATABASE_URL in Back4App → Settings → Environment Variables
# Get it from Supabase → Project Settings → Database → URI
# Use the "Transaction pooler" URL (port 6543), NOT the direct connection

_DB_URL = os.environ.get("DATABASE_URL", "")

if _DB_URL:
    # Parse the URL and configure Postgres
    _config = dj_database_url.parse(_DB_URL, conn_max_age=60)
    # Add SSL options required by Supabase
    if "OPTIONS" not in _config:
        _config["OPTIONS"] = {}
    _config["OPTIONS"]["sslmode"] = "require"
    DATABASES = {"default": _config}
else:
    # Fallback: SQLite in /tmp so the app can at least start
    # This is temporary — set DATABASE_URL in Back4App env vars!
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": "/tmp/labai_temp.db",
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

# Security - keep simple for Back4App
SECURE_BROWSER_XSS_FILTER   = True
X_FRAME_OPTIONS              = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True