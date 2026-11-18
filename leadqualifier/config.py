"""Paths and environment. API keys are read from the environment only and never logged.

TEACHING NOTE: a secret is a process-environment value. This module names the
variables; it never prints them. `APOLLO_ENRICH` gates organisation enrich only.
People Search gates on `APOLLO_API_KEY` alone. HubSpot write needs `HUBSPOT_WRITE=1`
and a token. Email-plugin **ready** is key + campaign id. SMS/Voice ready is Twilio SID +
token + from-number. Occupancy is a sqlite mount. Live Email skip is key +
campaign + `INSTANTLY_TEST_EMAIL`. Composition does not read a send flag.
⭐ ENFORCED BY: callers use these functions; 🔴 UNENFORCED: nothing
stops a caller from `os.environ.get` beside this file.
"""

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
RESULT_CACHE_FILE = CACHE_DIR / "answers.json"  # retired; answers live in SQLITE_PATH
SQLITE_PATH = Path(os.environ.get("FIRSTREAD_SQLITE", str(DATA_DIR / "firstread.sqlite")))
APOLLO_CACHE_DIR = CACHE_DIR / "apollo"
HUBSPOT_API = "https://api.hubapi.com"

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


def hubspot_token() -> str | None:
    for var in ("HUBSPOT_ACCESS_TOKEN", "HUBSPOT_PRIVATE_APP_TOKEN"):
        v = os.environ.get(var, "").strip()
        if v and not v.startswith("your-"):
            return v
    return None


def hubspot_write_enabled() -> bool:
    flag = os.environ.get("HUBSPOT_WRITE", "").strip().lower()
    return flag in ("1", "true", "yes", "on") and hubspot_token() is not None


def hubspot_test_contact_id() -> str | None:
    v = os.environ.get("HUBSPOT_TEST_CONTACT_ID", "").strip()
    return v or None


def instantly_api_key() -> str | None:
    v = os.environ.get("INSTANTLY_API_KEY", "").strip()
    return v if v and not v.startswith("your-") else None


def instantly_campaign_id() -> str | None:
    v = os.environ.get("INSTANTLY_CAMPAIGN_ID", "").strip()
    return v or None


def instantly_test_email() -> str | None:
    v = os.environ.get("INSTANTLY_TEST_EMAIL", "").strip()
    return v or None


def twilio_account_sid() -> str | None:
    v = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
    return v if v and not v.startswith("your-") else None


def twilio_auth_token() -> str | None:
    v = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    return v if v and not v.startswith("your-") else None


def twilio_from_number() -> str | None:
    v = os.environ.get("TWILIO_FROM_NUMBER", "").strip()
    return v or None


def workers() -> int:
    try:
        return max(1, int(os.environ.get("FIRSTREAD_WORKERS", "4")))
    except ValueError:
        return 4
