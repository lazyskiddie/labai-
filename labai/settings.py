"""
LabAI Django Settings
DB: Supabase PostgreSQL via DATABASE_URL env var
Host: Back4App Containers (port 8080)
"""
import os
import dj_database_url
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-change-this-in-production")

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

# ── DATABASE — Supabase PostgreSQL ────────────────────────────────
# Set DATABASE_URL on Back4App:
#   postgresql://postgres.[PROJECT]:[PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
DATABASE_URL = os.environ.get("DATABASE_URL", "")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # Local fallback — SQLite for development
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ── STATIC FILES — whitenoise ─────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ── APP CONFIG ────────────────────────────────────────────────────
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin@labai2024")

DATA_UPLOAD_MAX_MEMORY_SIZE  = 200 * 1024 * 1024   # 200 MB
FILE_UPLOAD_MAX_MEMORY_SIZE  = 200 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── SECURITY ──────────────────────────────────────────────────────
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER   = True
    X_FRAME_OPTIONS              = "DENY"
    SECURE_CONTENT_TYPE_NOSNIFF = True