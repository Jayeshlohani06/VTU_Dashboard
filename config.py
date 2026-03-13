"""
Centralized configuration loaded from environment variables / .env file.
Provides settings as typed values with sensible defaults.
"""

import os

# Try loading .env file if python-dotenv is available (optional dependency)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    """Application configuration sourced from environment."""

    # Server
    PORT = int(os.environ.get("PORT", 10000))
    HOST = os.environ.get("HOST", "127.0.0.1")
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

    # Caching
    CACHE_TYPE = os.environ.get("CACHE_TYPE", "SimpleCache")
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get("CACHE_DEFAULT_TIMEOUT", 3600))
    CACHE_THRESHOLD = int(os.environ.get("CACHE_THRESHOLD", 500))

    # Security
    SECRET_KEY = os.environ.get("SECRET_KEY", "vtu-dashboard-dev-key")
    MAX_UPLOAD_SIZE_MB = int(os.environ.get("MAX_UPLOAD_SIZE_MB", 10))
    RATE_LIMIT_FEEDBACK = int(os.environ.get("RATE_LIMIT_FEEDBACK", 5))

    # Google Sheets
    GOOGLE_SHEET_URL = os.environ.get("GOOGLE_SHEET_URL", "")
    GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS", "")

    # Feature Flags
    ENABLE_FEEDBACK = os.environ.get("ENABLE_FEEDBACK", "true").lower() == "true"
    ENABLE_TOUR = os.environ.get("ENABLE_TOUR", "true").lower() == "true"
