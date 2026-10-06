from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CREDENTIAL_FILE = Path.home() / ".vnstock" / "api_key.json"


def load_vnstock_env(*args, **kwargs) -> dict:
    """Return non-secret Vnstock Sponsor environment status."""
    os.environ.setdefault("VNSTOCK_INTERACTIVE", "0")
    os.environ.setdefault("VNSTOCK_LANGUAGE", "2")
    exists = CREDENTIAL_FILE.is_file()
    return {"credential_file": str(CREDENTIAL_FILE), "credential_file_exists": exists, "api_key_present": exists, "venv_path": os.getenv("VNSTOCK_VENV_PATH", "").strip()}


def require_vnstock_api_key() -> str:
    """Compatibility check only; never read or return the API key."""
    if not CREDENTIAL_FILE.is_file():
        raise RuntimeError("Vnstock Sponsor credential file not found at ~/.vnstock/api_key.json")
    return str(CREDENTIAL_FILE)
