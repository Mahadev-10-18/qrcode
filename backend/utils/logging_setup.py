import logging
import json
import re
from datetime import datetime, timezone

PHONE_RE = re.compile(r"\+?[1-9][0-9\-\s\(\)]{4,14}[0-9]")
EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
TWILIO_SID_RE = re.compile(r"AC[a-f0-9]{32}")
BEARER_RE = re.compile(r"bearer\s+[A-Za-z0-9\-\._~\+\/]+=*", flags=re.IGNORECASE)
AUTH_TOKEN_RE = re.compile(r"auth_token=[a-f0-9]{32}", flags=re.IGNORECASE)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": _utcnow().isoformat(),
            "level": record.levelname,
            "message": scrub_sensitive_info(record.getMessage()),
            "logger": record.name,
            "filename": record.filename,
            "lineno": record.lineno,
        }
        if record.exc_info:
            log_data["exception"] = scrub_sensitive_info(self.formatException(record.exc_info))

        return json.dumps(log_data)


def scrub_sensitive_info(text: str) -> str:
    if not text:
        return text

    cleaned = TWILIO_SID_RE.sub("[SCRUBBED_TWILIO_SID]", text)
    cleaned = EMAIL_RE.sub("[SCRUBBED_EMAIL]", cleaned)
    cleaned = PHONE_RE.sub("[SCRUBBED_PHONE]", cleaned)
    cleaned = AUTH_TOKEN_RE.sub("auth_token=[SCRUBBED]", cleaned)
    cleaned = BEARER_RE.sub("bearer [SCRUBBED]", cleaned)

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
