from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# Redis isn't available on this host's cPanel account, so fall back to an
# in-process local-memory cache. Not shared across worker processes, but
# avoids a hard dependency on infra we don't have here.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "HOST": env("EMAIL_HOST"),
        "PORT": env.int("EMAIL_PORT", default=587),
        "HOST_USER": env("EMAIL_HOST_USER"),
        "HOST_PASSWORD": env("EMAIL_HOST_PASSWORD"),
        "USE_TLS": env.bool("EMAIL_USE_TLS", default=True),
    },
}
