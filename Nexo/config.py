"""Configuration shared by the application factory and command line."""
import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DATABASE = os.environ.get("NEXO_DATABASE")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("NEXO_HTTPS") == "1"
