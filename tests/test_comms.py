"""FakeComms drain. Live Instantly is skipped without INSTANTLY_SEND.

TEACHING NOTE: Queue of Warm records a dispatch only when the payload has an
email. Demo L0*.json files have none — that is `no_address`, not a fake mailbox.
Drain takes Bindings, not a bare Comms. InstantlyEmail is Email-only.
"""

from __future__ import annotations

import json
import os

import httpx
import pytest

from leadqualifier.comms import (
    FakeComms,
    NoAddress,
    address_for,
    drain_outbound,
    fake_bindings,
    offer_text,
)
from leadqualifier.instantly import InstantlyEmail
from leadqualifier.ledger import get_ledger
from leadqualifier.leads import load_leads
from leadqualifier.workitem import (
    ApplyOk,
    Arrive,
    Calendar,
    CaseStudy,
    Copy,
    CsvRow,
    DeclineDraft,
    Draft,
    Email,
    Form,
    HandOff,
    ImportId,
    IcpVersionId,
    Judged,
    LinkedIn,
    QualifyingQuestion,
    Queue,
    RinglessVoicemail,
    Sms,
    Unjudged,
    Voice,
    email_draft,
    voice_draft,
)


def _warm():
    return Judged(IcpVersionId("v1"), "warm", False)


def test_queue_warm_without_email_is_no_address():
    load_leads()
    ledger = get_ledger()
    first = ledger.apply_command("L002", Queue(email_draft()), _warm())
    assert isinstance(first, ApplyOk)
    assert ledger.get_row("L002")["outbound_kind"] == "pending"
    comms = FakeComms()
    out = drain_outbound(ledger, fake_bindings(comms))
    assert out["failed"] == 1 and comms.calls == []
    assert ledger.get_row("L002")["outbound_kind"] == "failed"
    assert ledger.get_row("L002")["outbound_reason"] == "no_address"


def test_queue_warm_with_email_records_dispatch():
    ledger = get_ledger()
    payload = {
        "id": "C-mail",
        "source": "csv_import",
        "received_at": "2026-11-17T00:00:00Z",
        "person": {"name": "Ada", "email": "ada@secret.test"},
        "company": {"name": "Analytical", "domain": "analytical.de"},
        "message": {"text": "We drown in reports."},
    }
    born = ledger.apply_command(
        "C-mail", Arrive(CsvRow(ImportId("comms-1"), 1)), Unjudged(), payload=payload
    )
    assert isinstance(born, ApplyOk)
    queued = ledger.apply_command("C-mail", Queue(email_draft()), _warm())
    assert isinstance(queued, ApplyOk)
    comms = FakeComms()
    out = drain_outbound(ledger, fake_bindings(comms))
    assert out["dispatched"] == 1
    assert comms.calls[0]["address"] == "ada@secret.test"
    assert comms.calls[0]["channel"] == "email"
    assert ledger.get_row("C-mail")["outbound_kind"] == "dispatched"


def test_handoff_voice_with_phone_records_dispatch():
    ledger = get_ledger()
    payload = {
        "id": "C-voice",
        "source": "csv_import",
        "received_at": "2026-11-17T00:00:00Z",
        "person": {"name": "Kai", "email": "kai@berg.agency", "phone": "+494012345"},
        "company": {"name": "Berg", "domain": "berg.agency"},
        "message": {"text": "Book a founder call."},
    }
    ledger.apply_command("C-voice", Arrive(CsvRow(ImportId("comms-voice"), 1)), Unjudged(), payload=payload)
    hot = Judged(IcpVersionId("v1"), "hot", False)
    handed = ledger.apply_command("C-voice", HandOff(voice_draft()), hot)
    assert isinstance(handed, ApplyOk)
    comms = FakeComms()
    out = drain_outbound(ledger, fake_bindings(comms))
    assert out["dispatched"] == 1
    assert comms.calls[0]["channel"] == "voice"
    assert comms.calls[0]["address"] == "+494012345"


def test_unreviewed_cannot_dispatch():
    ledger = get_ledger()
    payload = {
        "id": "C-none",
        "source": "csv_import",
        "received_at": "2026-11-17T00:00:00Z",
        "person": {"name": "Bob", "email": "bob@secret.test"},
        "company": {"name": "B", "domain": "b.de"},
        "message": {"text": "Hi"},
    }
    ledger.apply_command("C-none", Arrive(CsvRow(ImportId("comms-2"), 1)), Unjudged(), payload=payload)
    comms = FakeComms()
    out = drain_outbound(ledger, fake_bindings(comms))
    assert out == {"dispatched": 0, "failed": 0}
    assert comms.calls == []


def test_reply_folds_into_payload():
    ledger = get_ledger()
    load_leads()
    from leadqualifier.workitem import Dismiss, RecordReply

    ledger.apply_command("L003", Dismiss(), _warm())
    out = ledger.apply_command("L003", RecordReply("we booked Tuesday"), Unjudged())
    assert isinstance(out, ApplyOk)
    payload = json.loads(ledger.get_row("L003")["payload_json"])
    assert payload["message"]["text"] == "we booked Tuesday"
    assert payload["message"].get("prior")


def test_instantly_posts_leads_endpoint(monkeypatch):
    seen: dict[str, object] = {}

    def fake_post(url, headers, json, timeout):
        seen["url"] = url
        seen["auth"] = headers.get("Authorization", "").startswith("Bearer ")
        seen["email"] = json["email"]
        seen["campaign"] = json["campaign"]
        req = httpx.Request("POST", url)
        return httpx.Response(200, json={"id": "lead-1"}, request=req)

    monkeypatch.setattr("leadqualifier.instantly.httpx.post", fake_post)
    comms = InstantlyEmail(token="tok", campaign_id="camp-1")
    remote = comms.dispatch(
        work_item_id="C-mail",
        channel=Email(),
        draft=email_draft(),
        payload={"person": {"name": "Ada Lovelace", "email": "ada@secret.test"}, "company": {"name": "Analytical"}},
    )
    assert remote == "lead-1"
    assert seen["url"] == "https://api.instantly.ai/api/v2/leads"
    assert seen["auth"] is True
    assert seen["email"] == "ada@secret.test"
    assert seen["campaign"] == "camp-1"


def test_instantly_no_address():
    comms = InstantlyEmail(token="tok", campaign_id="camp-1")
    try:
        comms.dispatch(
            work_item_id="x",
            channel=Email(),
            draft=email_draft(),
            payload={"person": {"name": "No Mail"}},
        )
        raise AssertionError("expected NoAddress")
    except NoAddress:
        pass


@pytest.mark.skipif(
    os.environ.get("INSTANTLY_SEND", "").strip().lower() not in ("1", "true", "yes", "on"),
    reason="INSTANTLY_SEND not set — live Instantly smoke is the owner's word",
)
def test_instantly_live_posts_test_address():
    """Probe POST https://api.instantly.ai/api/v2/leads — the route InstantlyEmail calls.

    🔴 UNENFORCED until INSTANTLY_SEND=1 plus INSTANTLY_API_KEY, INSTANTLY_CAMPAIGN_ID,
    INSTANTLY_TEST_EMAIL are in the environment. A skipped run proved nothing about Instantly.
    """
    token = os.environ.get("INSTANTLY_API_KEY", "").strip()
    campaign = os.environ.get("INSTANTLY_CAMPAIGN_ID", "").strip()
    email = os.environ.get("INSTANTLY_TEST_EMAIL", "").strip()
    if not token or not campaign or not email:
        pytest.skip("live Instantly env incomplete (key, campaign, test email)")
    comms = InstantlyEmail(token=token, campaign_id=campaign)
    remote = comms.dispatch(
        work_item_id="live-smoke",
        channel=Email(),
        draft=email_draft(),
        payload={"person": {"name": "First Read test", "email": email}, "company": {"name": "First Read"}},
    )
    assert remote  # Instantly's id; never print the key or the address.


def test_address_for_is_exhaustive():
    mail = {"person": {"email": "a@b.test", "phone": "+1", "linkedin": "https://linkedin.com/in/a"}, "company": {}}
    phone_only = {"person": {"email": "a@b.test", "phone": "+4940"}, "company": {}}
    li_company = {"person": {"email": "a@b.test"}, "company": {"linkedin": "https://linkedin.com/company/x"}}
    assert address_for(Email(), mail) == "a@b.test"
    assert address_for(LinkedIn(), mail) == "https://linkedin.com/in/a"
    assert address_for(LinkedIn(), li_company) == "https://linkedin.com/company/x"
    assert address_for(LinkedIn(), {"person": {"email": "a@b.test"}, "company": {}}) is None
    assert address_for(Voice(), phone_only) == "+4940"
    assert address_for(Sms(), phone_only) == "+4940"
    assert address_for(RinglessVoicemail(), phone_only) == "+4940"
    assert address_for(Voice(), {"person": {"email": "a@b.test"}, "company": {}}) is None


def test_offer_text_is_exhaustive():
    assert offer_text(Copy("Hi")) == "Hi"
    assert offer_text(QualifyingQuestion("how many?")) == "how many?"
    assert offer_text(DeclineDraft("no")) == "no"
    assert offer_text(Calendar(("Tue", "Thu"))) == "Tue or Thu"
    assert offer_text(CaseStudy("https://example.test/cs")) == "https://example.test/cs"
    assert offer_text(Form("https://example.test/form")) == "https://example.test/form"


def test_fake_comms_records_offer_text_not_body():
    ledger = get_ledger()
    payload = {
        "id": "C-offer",
        "source": "csv_import",
        "received_at": "2026-11-18T00:00:00Z",
        "person": {"name": "Ada", "email": "ada@secret.test"},
        "company": {"name": "Analytical", "domain": "analytical.de"},
        "message": {"text": "We drown in reports."},
    }
    ledger.apply_command("C-offer", Arrive(CsvRow(ImportId("comms-offer"), 1)), Unjudged(), payload=payload)
    queued = ledger.apply_command("C-offer", Queue(email_draft("Hi — case study")), _warm())
    assert isinstance(queued, ApplyOk)
    comms = FakeComms()
    out = drain_outbound(ledger, fake_bindings(comms))
    assert out["dispatched"] == 1
    assert comms.calls[0]["text"] == "Hi — case study"
    assert "body" not in comms.calls[0]


def test_linkedin_does_not_use_email():
    comms = FakeComms()
    try:
        comms.dispatch(
            work_item_id="li",
            channel=LinkedIn(),
            draft=Draft(LinkedIn(), Copy("hi")),
            payload={"person": {"email": "ada@secret.test"}},
        )
        raise AssertionError("expected NoAddress")
    except NoAddress:
        pass
