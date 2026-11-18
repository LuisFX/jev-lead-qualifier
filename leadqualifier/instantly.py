"""Email host adapter: POST /api/v2/leads.

TEACHING NOTE: this file binds Email only. Drain looks up Bindings[email].
It does not mention other channels. A missing map key is `channel_unbound`
in `comms.py`, not here.

⭐ ENFORCED BY: `tests/test_bindings.py` (this file names Email only);
`tests/test_comms.py` mocked POST. Live send is skipped unless INSTANTLY_SEND=1.
"""

from __future__ import annotations

from typing import Any

import httpx

from . import config
from .comms import NoAddress, address_for, offer_text
from .workitem import Channel, Draft, Email

INSTANTLY_LEADS = "https://api.instantly.ai/api/v2/leads"


class InstantlyEmail:
    """POST /api/v2/leads — the endpoint this product calls, not a status URL."""

    def __init__(self, token: str | None = None, campaign_id: str | None = None):
        self.token = token if token is not None else config.instantly_api_key()
        self.campaign_id = campaign_id if campaign_id is not None else config.instantly_campaign_id()

    def dispatch(self, *, work_item_id: str, channel: Channel, draft: Draft, payload: dict[str, Any]) -> str:
        if not isinstance(channel, Email):
            raise AssertionError(f"unhandled: {type(channel).__name__}")
        if not self.token:
            raise RuntimeError("INSTANTLY_API_KEY is not set")
        if not self.campaign_id:
            raise RuntimeError("INSTANTLY_CAMPAIGN_ID is not set")
        email = address_for(Email(), payload)
        if email is None:
            raise NoAddress()
        person = payload.get("person") or {}
        company = payload.get("company") or {}
        name = str(person.get("name") or "")
        parts = name.split(None, 1)
        first = parts[0] if parts else ""
        last = parts[1] if len(parts) > 1 else ""
        r = httpx.post(
            INSTANTLY_LEADS,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                # Cloudflare 1010's a default Python UA; Instantly still sees the Bearer.
                "User-Agent": "FirstRead/1.0 (email-adapter)",
            },
            json={
                "campaign": self.campaign_id,
                "email": email,
                "personalization": offer_text(draft.offer),
                "first_name": first,
                "last_name": last,
                "company_name": company.get("name") or person.get("company") or "",
                "job_title": person.get("title") or "",
                "website": company.get("domain") or "",
            },
            timeout=12.0,
        )
        if r.status_code >= 400:
            raise RuntimeError(f"email adapter POST /api/v2/leads HTTP {r.status_code}")
        data = r.json() if r.content else {}
        remote = str(data.get("id") or "")
        return remote or f"email-{work_item_id}"
