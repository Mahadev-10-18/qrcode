import logging
import json
import re
from datetime import datetime, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": _utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "filename": record.filename,
            "lineno": record.lineno
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Scrub credentials, phone_numbers, auth tokens
        log_data["message"] = scrub_sensitive_info(log_data["message"])
        if "exception" in log_data:
            log_data["exception"] = scrub_sensitive_info(log_data["exception"])

        return json.dumps(log_data)


def scrub_sensitive_info(text: str) -> str:
    if not text:
        return text

    # regex-scrub E.164 phone numbers (5 to 15 digits sequence, optionally starting with +)
    # Match strings of digits that look like phone numbers (5 to 15 digits, optionally prefixed by +)
    # We replace +1111111111, +15559876543, 1111111111, 2222222222, etc.
    # To avoid scrubbing small numbers (like tag counts), we match sequences of 5-15 digits.
    # We also allow dashes, parentheses, or spaces within the sequence if we want to be safe, but E.164 is standard.
    # Regex: replace sequences of 5 or more consecutive digits, plus optional leading plus:
    cleaned = re.sub(r"\+?[0-9][0-9\-\s\(\)]{4,14}[0-9]", "[SCRUBBED_PHONE]", text)

    # Scrub Twilio SIDs
    cleaned = re.sub(r"AC[a-f0-9]{32}", "[SCRUBBED_TWILIO_SID]", cleaned)

    # Scrub basic token patterns or auth headers
    cleaned = re.sub(r"auth_token=[a-f0-9]{32}", "auth_token=[SCRUBBED]", cleaned)
    cleaned = re.sub(r"bearer\s+[A-Za-z0-9\-\._~\+\/]+=*", "bearer [SCRUBBED]", cleaned, flags=re.IGNORECASE)

    return cleaned


def setup_logging():
    # Set root logger level
    logging.getLogger().setLevel(logging.INFO)

    formatter = JsonFormatter()

    # Configure root logger handler
    root_logger = logging.getLogger()
    # Remove existing handlers to avoid duplicate output formatters
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Redirect uvicorn and fastapi log handlers to root handler
    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        log = logging.getLogger(logger_name)
        log.handlers = []
        log.propagate = True
