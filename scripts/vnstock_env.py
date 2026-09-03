from __future__ import annotations

"""Local-only environment loader for Vnstock Sponsor credentials.

The Sponsor library (vnstock_data) automatically reads VNSTOCK_API_KEY from the
process environment.  This helper loads a project-root .env file *before* any
vnstock_data import.  The key is never printed, written to CSV, or pushed to
GitHub.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"


def _parse_env_line(line: str):
    s = line.strip()
    if not s or s.startswith("#") or "=" not in s:
        return None, None
    key, value = s.split("=", 1)
    key = key.strip()
    value = value.strip()
    if value and value[0:1] in {"'", '"'} and value[-1:] == value[0]:
        value = value[1:-1]
    return key, value


def load_vnstock_env(env_file: Path | None = None, override: bool = False) -> dict:
    """Load .env into os.environ and return non-secret status information."""
    path = Path(env_file) if env_file else ENV_FILE
    loaded = []
    if path.exists():
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            key, value = _parse_env_line(raw)
            if not key:
                continue
            if override or key not in os.environ:
                os.environ[key] = value
            loaded.append(key)

    # Sponsor installer/library can operate non-interactively once the key is
    # present. Do not override a deliberate user setting.
    os.environ.setdefault("VNSTOCK_INTERACTIVE", "0")
    os.environ.setdefault("VNSTOCK_LANGUAGE", "2")

    key = os.getenv("VNSTOCK_API_KEY", "").strip()
    return {
        "env_file": str(path),
        "env_file_exists": path.exists(),
        "loaded_keys": loaded,
        "api_key_present": bool(key),
        "api_key_masked": mask_secret(key),
        "venv_path": os.getenv("VNSTOCK_VENV_PATH", "").strip(),
    }


def mask_secret(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return "NOT SET"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def require_vnstock_api_key() -> str:
    load_vnstock_env()
    key = os.getenv("VNSTOCK_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "VNSTOCK_API_KEY is not configured. Run SETUP_VNSTOCK_BRONZE.bat "
            "or copy .env.example to .env and fill VNSTOCK_API_KEY."
        )
    return key
