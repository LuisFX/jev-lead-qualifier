"""HubSpot write adapter. Keys from the environment only — never a file.

TEACHING NOTE: this is a port. The aggregate emits `RelayPending`; this module
delivers, then the host applies `MarkDelivered` / `MarkFailed`. Existing account
→ a note on the company, not a new contact. Smoke uses a test contact, never a
real party's record.

⭐ ENFORCED BY: `tests/test_relay.py`. Live HTTP is skipped unless `HUBSPOT_WRITE=1`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

import httpx

from . import config

API = "https://api.hubapi.com"


def properties_from_result(result: dict[str, Any]) -> dict[str, str]:
    route = result.get("route") or {}
    action = result.get("next_action") or {}
    return {
        "tier": str(result.get("tier") or ""),
        "route": str(route.get("label") or ""),
        "fit": str(result.get("fit") if result.get("fit") is not None else ""),
        "intent": str(result.get("intent") if result.get("intent") is not None else ""),
        "primary_pain": str(result.get("primary_pain") or ""),
        "next_action": str(action.get("label") or action.get("text") or ""),
    }


def note_body(result: dict[str, Any]) -> str:
    props = properties_from_result(result)
    why = " · ".join(result.get("why") or [])
    return (
        f"First Read · {props['tier']}\n"
        f"fit {props['fit']} · intent {props['intent']}\n"
        f"route {props['route']}\n"
        f"pain {props['primary_pain']}\n"
        f"next {props['next_action']}\n"
        f"{why}"
    )


class Writer(Protocol):
    def write(
        self,
        *,
        work_item_id: str,
        icp_version_id: str,
        result: dict[str, Any],
        payload: dict[str, Any],
        existing_account: bool,
    ) -> str: ...


class FakeWriter:
    """In-process writer for tests. Records calls; never touches HubSpot."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def write(
        self,
        *,
        work_item_id: str,
        icp_version_id: str,
        result: dict[str, Any],
        payload: dict[str, Any],
        existing_account: bool,
    ) -> str:
        remote = f"fake-{work_item_id}-{icp_version_id[:8]}"
        self.calls.append(
            {
                "work_item_id": work_item_id,
                "icp_version_id": icp_version_id,
                "existing_account": existing_account,
                "properties": properties_from_result(result),
                "remote_id": remote,
            }
        )
        return remote


class HubSpotWriter:
    def __init__(self, token: str | None = None, test_contact_id: str | None = None):
        self.token = token if token is not None else config.hubspot_token()
        self.test_contact_id = test_contact_id if test_contact_id is not None else config.hubspot_test_contact_id()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token or ''}", "Content-Type": "application/json"}

    def write(
        self,
        *,
        work_item_id: str,
        icp_version_id: str,
        result: dict[str, Any],
        payload: dict[str, Any],
        existing_account: bool,
    ) -> str:
        if not self.token:
            raise RuntimeError("HUBSPOT_ACCESS_TOKEN is not set")
        props = properties_from_result(result)
        note = note_body(result)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        if existing_account:
            company_id = (payload.get("hubspot_company_id") or (result.get("existing_account") or {}).get("id"))
            if not company_id:
                raise RuntimeError("existing account has no HubSpot company id")
            return self._note_on("companies", str(company_id), note, ts, work_item_id, icp_version_id)
        contact_id = self.test_contact_id or payload.get("hubspot_contact_id")
        if not contact_id:
            raise RuntimeError("no test contact id — set HUBSPOT_TEST_CONTACT_ID")
        r = httpx.patch(
            f"{API}/crm/v3/objects/contacts/{contact_id}",
            headers=self._headers(),
            json={"properties": props},
            timeout=12.0,
        )
        if r.status_code >= 400:
            raise RuntimeError(f"HubSpot contact PATCH HTTP {r.status_code}")
        self._note_on("contacts", str(contact_id), note, ts, work_item_id, icp_version_id)
        return f"hs-contact-{contact_id}"

    def _note_on(self, object_type: str, object_id: str, body: str, ts: str, work_item_id: str, icp_version_id: str) -> str:
        r = httpx.post(
            f"{API}/crm/v3/objects/notes",
            headers=self._headers(),
            json={"properties": {"hs_note_body": body, "hs_timestamp": ts}},
            timeout=12.0,
        )
        if r.status_code >= 400:
            raise RuntimeError(f"HubSpot note POST HTTP {r.status_code}")
        note_id = str((r.json() or {}).get("id") or "")
        if note_id:
            to_type = "companies" if object_type == "companies" else "contacts"
            httpx.put(
                f"{API}/crm/v3/objects/notes/{note_id}/associations/{to_type}/{object_id}/note_to_{to_type[:-1] if to_type.endswith('s') else to_type}",
                headers=self._headers(),
                timeout=12.0,
            )
        return f"hs-note-{note_id or work_item_id}"
