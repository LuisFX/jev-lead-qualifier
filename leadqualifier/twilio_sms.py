"""SMS host adapter: POST Accounts/{sid}/Messages.json.

TEACHING NOTE: this file binds Sms only. The catalog registers it as
`sms-plugin`. Drain looks up Bindings[sms]. It does not mention Email or Voice.
Ready is SID + token + from-number in the process environment. Occupancy is a
mount. A missing map key is `channel_unbound` in `comms.py`, not here.

⭐ ENFORCED BY: `tests/test_integrations.py` (mocked POST, no live Twilio).
"""

from __future__ import annotations

from typing import Any

import httpx

from . import config
from .comms import NoAddress, address_for, offer_text
from .workitem import Channel, Draft, Sms

TWILIO_MESSAGES = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


class TwilioSms:
    """POST Messages.json — the endpoint this product calls, not a status URL."""

    def __init__(
        self,
        account_sid: str | None = None,
        auth_token: str | None = None,
        from_number: str | None = None,
    ):
        self.account_sid = account_sid if account_sid is not None else config.twilio_account_sid()
        self.auth_token = auth_token if auth_token is not None else config.twilio_auth_token()
        self.from_number = from_number if from_number is not None else config.twilio_from_number()

    def dispatch(self, *, work_item_id: str, channel: Channel, draft: Draft, payload: dict[str, Any]) -> str:
        if not isinstance(channel, Sms):
            raise AssertionError(f"unhandled: {type(channel).__name__}")
        if not self.account_sid:
            raise RuntimeError("TWILIO_ACCOUNT_SID is not set")
        if not self.auth_token:
            raise RuntimeError("TWILIO_AUTH_TOKEN is not set")
        if not self.from_number:
            raise RuntimeError("TWILIO_FROM_NUMBER is not set")
        phone = address_for(Sms(), payload)
        if phone is None:
            raise NoAddress()
        url = TWILIO_MESSAGES.format(sid=self.account_sid)
        r = httpx.post(
            url,
            auth=(self.account_sid, self.auth_token),
            data={"To": phone, "From": self.from_number, "Body": offer_text(draft.offer)},
            timeout=12.0,
        )
        if r.status_code >= 400:
            raise RuntimeError(f"sms adapter POST Messages.json HTTP {r.status_code}")
        data = r.json() if r.content else {}
        remote = str(data.get("sid") or "")
        return remote or f"sms-{work_item_id}"
