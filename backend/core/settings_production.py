from .settings import *

DEBUG = False

SECRET_KEY = "esg-secret-key-production"

ALLOWED_HOSTS = [
    "esg-platform-production-c417.up.railway.app",
    "mindful-motivation-production-6d84.up.railway.app",
    "localhost",
    "127.0.0.1",
]

CORS_ALLOW_ALL_ORIGINS = True

CSRF_TRUSTED_ORIGINS = [
    "https://mindful-motivation-production-6d84.up.railway.app",
    "https://esg-platform-production-c417.up.railway.app",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"