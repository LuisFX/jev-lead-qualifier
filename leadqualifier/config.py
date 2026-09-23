"""Paths and environment. API keys are read from the environment only and never logged."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
WEB_DIR = ROOT / "web"
LEADS_DIR = DATA_DIR / "leads"
ICP_FILE = DATA_DIR / "icp.json"
ICP_PRESETS_DIR = DATA_DIR / "icp_presets"
DEFAULT_PRESET = "lanternfield_agencies"
CRM_FILE = DATA_DIR / "crm.json"
GOLD_FILE = DATA_DIR / "gold.json"
PLAYBOOK_FILE = DATA_DIR / "playbook.json"
CACHE_DIR = Path(os.environ.get("FIRSTREAD_CACHE_DIR", str(DATA_DIR / "cache")))
RESULT_CACHE_FILE = CACHE_DIR / "answers.json"
APOLLO_CACHE_DIR = CACHE_DIR / "apollo"

MISSING_KEY_MESSAGE = (
    "Add your TypeSafe key to run this live: put TYPESAFE_API_KEY=… in .env "
    "(copy .env.example) and restart ./run.sh serve."
)


def typesafe_api_key() -> str | None:
    for var in ("TYPESAFE_API_KEY", "JEV_API_KEY"):
        v = os.environ.get(var, "").strip()
        if v and not v.startswith("your-"):
            return v
    return None


def apollo_api_key() -> str | None:
    v = os.environ.get("APOLLO_API_KEY", "").strip()
    return v if v and not v.startswith("your-") else None


def apollo_enabled() -> bool:
    flag = os.environ.get("APOLLO_ENRICH", "").strip().lower()
    return flag in ("1", "true", "yes", "on") and apollo_api_key() is not None


def workers() -> int:
    try:
        return max(1, int(os.environ.get("FIRSTREAD_WORKERS", "4")))
    except ValueError:
        return 4
