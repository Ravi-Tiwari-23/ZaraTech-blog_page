from .settings import *
import os


# =========================================================
# INSTALLED APPS - MONGODB
# =========================================================

INSTALLED_APPS = [
    "blog_main.apps.MongoAdminConfig",
    "blog_main.apps.MongoAuthConfig",
    "blog_main.apps.MongoContentTypesConfig",

    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sitemaps",
    "django.contrib.staticfiles",

    "django_mongodb_backend",

    # Cloudinary
    "cloudinary_storage",
    "cloudinary",

    # Project apps
    "blogs.apps.MongoBlogsConfig",
    "assignments.apps.MongoAssignmentsConfig",
    "crispy_forms",
    "crispy_bootstrap4",
    "dashboards",
]


# =========================================================
# MONGODB DATABASE
# =========================================================

DATABASES = {
    "default": {
        "ENGINE": "django_mongodb_backend",
        "HOST": os.environ.get("MONGODB_URI"),
        "NAME": os.environ.get("MONGODB_NAME", "genvilla_db"),
    }
}


# =========================================================
# CLOUDINARY
# =========================================================

CLOUDINARY_STORAGE = {
    "CLOUD_NAME": os.environ.get("CLOUDINARY_CLOUD_NAME"),
    "API_KEY": os.environ.get("CLOUDINARY_API_KEY"),
    "API_SECRET": os.environ.get("CLOUDINARY_API_SECRET"),
}


# =========================================================
# MONGODB OBJECT ID
# =========================================================

DEFAULT_AUTO_FIELD = "django_mongodb_backend.fields.ObjectIdAutoField"


# =========================================================
# MONGODB MIGRATIONS
# =========================================================

MIGRATION_MODULES = {
    "admin": "mongo_migrations.admin",
    "auth": "mongo_migrations.auth",
    "contenttypes": "mongo_migrations.contenttypes",
    "dashboards": "mongo_migrations.dashboards",
    "blogs": "mongo_migrations.blogs",
    "assignments": "mongo_migrations.assignments",
}


# =========================================================
# ENVIRONMENT / SECURITY
# =========================================================

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")

DEBUG = os.environ.get(
    "DJANGO_DEBUG",
    "False"
).lower() == "true"


ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        "127.0.0.1,localhost"
    ).split(",")
    if host.strip()
]


CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        ""
    ).split(",")
    if origin.strip()
]


# =========================================================
# MIDDLEWARE
# WhiteNoise MUST be directly after SecurityMiddleware
# =========================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# =========================================================
# STATIC FILES
# =========================================================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"


# =========================================================
# STORAGE
#
# Uploaded media -> Cloudinary
# Static CSS/JS -> WhiteNoise
# =========================================================

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },

    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


# =========================================================
# PRODUCTION SECURITY
# These activate only when DJANGO_DEBUG=False
# =========================================================

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    SECURE_SSL_REDIRECT = True

    SECURE_HSTS_SECONDS = 3600
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
