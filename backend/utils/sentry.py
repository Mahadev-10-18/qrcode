import logging
import re
from typing import Any, Dict, Optional

from ..config import settings

logger = logging.getLogger(__name__)

PHONE_RE = re.compile(r"\+?\d{7,15}")
EMAIL_RE = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
TWILIO_SID_RE = re.compile(r"AC[a-f0-9]{32}")


def _scrub_value(value: Any) -> Any:
    if isinstance(value, str):
        value = TWILIO_SID_RE.sub("[SCRUBBED_TWILIO_SID]", value)
        value = PHONE_RE.sub("[SCRUBBED_PHONE]", value)
        value = EMAIL_RE.sub("[SCRUBBED_EMAIL]", value)
        return value
    if isinstance(value, dict):
        return {k: _scrub_value(v) if k not in ("level", "logger") else v for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub_value(v) for v in value]
    return value


def _scrub_event(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for key in ("message", "culprit", "transaction"):
        if key in event and isinstance(event[key], str):
            event[key] = _scrub_value(event[key])

    if "exception" in event:
        for exc in event["exception"].get("values", []):
            if "value" in exc:
                exc["value"] = _scrub_value(exc["value"])
            if "mechanism" in exc and "data" in exc["mechanism"]:
                exc["mechanism"]["data"] = _scrub_value(exc["mechanism"]["data"])

    if "request" in event:
        req = event["request"]
        for field in ("data", "query_string", "cookies", "headers"):
            if field in req:
                req[field] = _scrub_value(req[field])

    if "extra" in event:
        event["extra"] = _scrub_value(event["extra"])

    if "contexts" in event:
        event["contexts"] = _scrub_value(event["contexts"])

    if "breadcrumbs" in event:
        for bc in event["breadcrumbs"].get("values", []):
            if "message" in bc:
                bc["message"] = _scrub_value(bc["message"])
            if "data" in bc:
                bc["data"] = _scrub_value(bc["data"])

    if "user" in event:
        user = event["user"]
        for sensitive_key in ("email", "phone", "phone_number", "username", "ip_address"):
            if sensitive_key in user:
                user[sensitive_key] = _scrub_value(user[sensitive_key])

    return event


def init_sentry() -> None:
    dsn = settings.sentry_dsn.strip() if settings.sentry_dsn else ""
    if not dsn:
        logger.info("Sentry DSN not set — skipping Sentry initialization.")
        return

    import sentry_sdk

    sentry_sdk.init(
        dsn=dsn,
        before_send=_scrub_event,
        traces_sample_rate=0.0,
        send_default_pii=False,
    )
    logger.info("Sentry initialized with DSN.")
