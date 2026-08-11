import os

from .base import *  # noqa: F403
from .base import database_config

DEBUG = False
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DATABASES = {"default": database_config(os.environ["DATABASE_URL"])}
ALLOWED_HOSTS = [
    host.strip() for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if host.strip()
]
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
