"""Configuration shared by the application factory and command line."""
import os
from datetime import timedelta

class Config:
    PRODUCTION = os.environ.get('NEXO_ENV') == 'production'
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DATABASE = os.environ.get("NEXO_DATABASE")
    UPLOAD_FOLDER = os.environ.get("NEXO_UPLOAD_FOLDER")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = PRODUCTION or os.environ.get("NEXO_HTTPS") == "1"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_REFRESH_EACH_REQUEST = False
    MAX_FORM_MEMORY_SIZE = 256 * 1024
    MAX_FORM_PARTS = 50
    TRUSTED_HOSTS = [v.strip() for v in os.environ.get('NEXO_TRUSTED_HOSTS', '').split(',') if v.strip()] or None
    AUTH_RATE_LIMIT = 60
    AUTH_RATE_WINDOW = 900
