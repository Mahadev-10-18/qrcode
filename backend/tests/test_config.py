import pytest
import os
import sys
import importlib
from pydantic import ValidationError

def test_config_fails_loudly_when_unset():
    # Keep track of current env
    old_env = os.environ.copy()
    
    # Temporarily remove required environment variables
    required_keys = ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PROXY_SERVICE_SID"]
    for key in required_keys:
        if key in os.environ:
            del os.environ[key]
            
    # Unload the config module if it was already imported, so it re-evaluates
    if "backend.config" in sys.modules:
        del sys.modules["backend.config"]
        
    try:
        # Expect ValidationError on startup if Twilio settings are missing
        with pytest.raises(ValidationError) as exc_info:
            importlib.import_module("backend.config")
        
        # Verify it lists the missing keys in the validation error
        err_msg = str(exc_info.value)
        assert "TWILIO_ACCOUNT_SID" in err_msg or "twilio_account_sid" in err_msg
    finally:
        # Restore environment
        os.environ.clear()
        os.environ.update(old_env)
        
        # Reload configuration with restored environment
        if "backend.config" in sys.modules:
            del sys.modules["backend.config"]
        importlib.import_module("backend.config")
