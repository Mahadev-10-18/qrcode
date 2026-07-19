import pytest
import os
import sys
import importlib


def test_production_config_rejects_insecure_defaults():
    old_env = os.environ.copy()

    old_app_env = os.environ.get("APP_ENV", "")
    os.environ["APP_ENV"] = "production"
    os.environ["SECRET_KEY"] = "changeme"

    env_files = [".env", "backend/.env"]
    renamed_files = []
    for f in env_files:
        if os.path.exists(f):
            os.rename(f, f + ".bak")
            renamed_files.append(f)

    if "backend.config" in sys.modules:
        del sys.modules["backend.config"]

    try:
        with pytest.raises(ValueError):
            importlib.import_module("backend.config")
    finally:
        for f in renamed_files:
            if os.path.exists(f + ".bak"):
                os.rename(f + ".bak", f)

        os.environ.clear()
        os.environ.update(old_env)
        # Restore APP_ENV
        if old_app_env:
            os.environ["APP_ENV"] = old_app_env

        if "backend.config" in sys.modules:
            del sys.modules["backend.config"]
        importlib.import_module("backend.config")
