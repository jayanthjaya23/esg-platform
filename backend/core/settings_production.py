from .settings import *

DEBUG = False

SECRET_KEY = "esg-secret-key-production"

ALLOWED_HOSTS = ["*"]

CORS_ALLOW_ALL_ORIGINS = True

CSRF_TRUSTED_ORIGINS = [
    "https://mindful-motivation-production-6d84.up.railway.app",
    "https://esg-platform-production-c417.up.railway.app",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"