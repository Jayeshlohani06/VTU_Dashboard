"""
Input validation and security helpers for VTU Dashboard.
Validates file uploads, sanitizes inputs, and enforces limits.
"""

import base64
import re
from config import Config
from logging_config import get_logger

logger = get_logger("security")

# Excel file magic bytes signatures
EXCEL_SIGNATURES = {
    b"\x50\x4b\x03\x04": "xlsx (ZIP-based)",   # .xlsx
    b"\xd0\xcf\x11\xe0": "xls (OLE2)",          # .xls
}

# Allowed MIME types
ALLOWED_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
    "application/vnd.ms-excel",  # xls
    "text/csv",
    "application/csv",
    "application/octet-stream",  # generic binary (sometimes used)
}

# Max filename length
MAX_FILENAME_LENGTH = 255


def validate_upload(contents, filename):
    """
    Validate an uploaded file for security.
    Returns (is_valid, error_message).
    """
    if not contents or not filename:
        return False, "No file provided."

    # --- Filename validation ---
    if len(filename) > MAX_FILENAME_LENGTH:
        logger.warning("Rejected upload: filename too long (%d chars)", len(filename))
        return False, "Filename is too long."

    # Sanitize filename — strip path traversal attempts
    safe_name = re.sub(r'[^\w\s\-.]', '', filename)
    if safe_name != filename:
        logger.warning("Suspicious filename detected: %s", filename)

    # Check extension
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in {"xlsx", "xls", "csv"}:
        logger.warning("Rejected upload: invalid extension '%s'", ext)
        return False, f"Invalid file type '.{ext}'. Only .xlsx, .xls, .csv files are allowed."

    # --- Size validation ---
    try:
        content_type, content_string = contents.split(",", 1)
        decoded = base64.b64decode(content_string)
    except Exception:
        logger.warning("Rejected upload: failed to decode base64 content")
        return False, "Could not read the uploaded file."

    size_mb = len(decoded) / (1024 * 1024)
    max_size = Config.MAX_UPLOAD_SIZE_MB
    if size_mb > max_size:
        logger.warning("Rejected upload: file too large (%.1f MB > %d MB limit)", size_mb, max_size)
        return False, f"File is too large ({size_mb:.1f} MB). Maximum allowed size is {max_size} MB."

    # --- Magic bytes validation (for Excel files) ---
    if ext in {"xlsx", "xls"}:
        first_bytes = decoded[:4]
        if not any(decoded.startswith(sig) for sig in EXCEL_SIGNATURES):
            logger.warning("Rejected upload: magic bytes mismatch for '%s' (got %s)", filename, first_bytes.hex())
            return False, "File does not appear to be a valid Excel file. The file may be corrupted."

    logger.info("Upload validated: %s (%.2f MB)", filename, size_mb)
    return True, None


def sanitize_text(text, max_length=500):
    """Sanitize user text input — strip HTML tags and limit length."""
    if not text:
        return ""
    # Remove HTML tags
    cleaned = re.sub(r'<[^>]+>', '', str(text))
    # Limit length
    return cleaned[:max_length].strip()


def validate_email(email):
    """Basic email format validation."""
    if not email:
        return True  # Email is optional
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


class RateLimiter:
    """Simple in-memory rate limiter for feedback submissions."""

    def __init__(self, max_requests=None, window_seconds=60):
        self.max_requests = max_requests or Config.RATE_LIMIT_FEEDBACK
        self.window = window_seconds
        self._requests = {}  # ip/key -> list of timestamps

    def is_allowed(self, key):
        """Check if a request from the given key is allowed."""
        import time
        now = time.time()
        if key not in self._requests:
            self._requests[key] = []

        # Remove old entries outside the window
        self._requests[key] = [t for t in self._requests[key] if now - t < self.window]

        if len(self._requests[key]) >= self.max_requests:
            logger.warning("Rate limit exceeded for key: %s", key)
            return False

        self._requests[key].append(now)
        return True


# Singleton rate limiter for feedback
feedback_limiter = RateLimiter()
