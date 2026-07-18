from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.main import app
from backend.utils.sentry import _scrub_event

client = TestClient(app)


class TestSentryScrubbing:
    def test_scrubs_phone_in_exception_value(self):
        event = {
            "exception": {
                "values": [
                    {"value": "contacted owner at +15551234567 and +15559876543"}
                ]
            }
        }
        result = _scrub_event(event, {})
        val = result["exception"]["values"][0]["value"]
        assert "[SCRUBBED_PHONE]" in val
        assert "+15551234567" not in val
        assert "+15559876543" not in val

    def test_scrubs_email_in_exception_value(self):
        event = {
            "exception": {
                "values": [
                    {"value": "user test@example.com not found"}
                ]
            }
        }
        result = _scrub_event(event, {})
        val = result["exception"]["values"][0]["value"]
        assert "[SCRUBBED_EMAIL]" in val
        assert "test@example.com" not in val

    def test_scrubs_phone_in_extra(self):
        event = {
            "extra": {
                "finder_phone": "+15551234567",
                "owner_phone": "1111111111",
            }
        }
        result = _scrub_event(event, {})
        assert "[SCRUBBED_PHONE]" in result["extra"]["finder_phone"]
        assert "[SCRUBBED_PHONE]" in result["extra"]["owner_phone"]
        assert "+15551234567" not in result["extra"]["finder_phone"]

    def test_scrubs_email_in_user_context(self):
        event = {
            "user": {
                "email": "victim@example.com",
                "phone": "+15551234567",
                "ip_address": "192.168.1.1",
            }
        }
        result = _scrub_event(event, {})
        assert "[SCRUBBED_EMAIL]" in result["user"]["email"]
        assert "[SCRUBBED_PHONE]" in result["user"]["phone"]
        assert "victim@example.com" not in result["user"]["email"]
        assert "+15551234567" not in result["user"]["phone"]

    def test_scrubs_twilio_sid_in_message(self):
        sid = "AC" + "0123456789abcdef" + "0123456789abcdef"
        event = {
            "message": f"Twilio SID {sid} created"
        }
        result = _scrub_event(event, {})
        assert "[SCRUBBED_TWILIO_SID]" in result["message"]
        assert sid not in result["message"]


    def test_scrubs_breadcrumbs(self):
        event = {
            "breadcrumbs": {
                "values": [
                    {"message": "calling +15551234567"},
                    {"data": {"phone": "+15559876543"}},
                ]
            }
        }
        result = _scrub_event(event, {})
        bc = result["breadcrumbs"]["values"]
        assert "[SCRUBBED_PHONE]" in bc[0]["message"]
        assert "[SCRUBBED_PHONE]" in bc[1]["data"]["phone"]

    def test_scrubs_request_data(self):
        event = {
            "request": {
                "data": "phone_number=%2B15551234567&email=test%40example.com",
                "headers": {"X-Forwarded-For": "192.168.1.1"},
            }
        }
        result = _scrub_event(event, {})
        assert "[SCRUBBED_PHONE]" in result["request"]["data"]
        assert "15551234567" not in result["request"]["data"]

    def test_returns_none_gracefully(self):
        result = _scrub_event({"message": "safe log entry"}, {})
        assert result["message"] == "safe log entry"

    def test_passes_through_non_string_data(self):
        event = {"exception": {"values": [{}]}}
        result = _scrub_event(event, {})
        assert result == event


class TestSentryInit:
    def test_init_sentry_no_dsn_does_nothing(self):
        from backend.utils.sentry import init_sentry
        from backend.config import settings
        original = settings.sentry_dsn
        settings.sentry_dsn = ""
        try:
            init_sentry()
        finally:
            settings.sentry_dsn = original

    def test_init_sentry_with_dsn_calls_sdk(self):
        from backend.utils.sentry import init_sentry
        dsn = "https://key@o0.ingest.sentry.io/0"
        with patch("backend.utils.sentry.settings") as mock_settings:
            mock_settings.sentry_dsn = dsn
            with patch("sentry_sdk.init") as mock_init:
                init_sentry()
                mock_init.assert_called_once()
                args, kwargs = mock_init.call_args
                assert kwargs["dsn"] == dsn
                assert kwargs["send_default_pii"] is False


class TestDebugSentry:
    def test_debug_sentry_raises_runtime_error(self):
        import pytest
        with pytest.raises(RuntimeError):
            client.get("/debug-sentry")
