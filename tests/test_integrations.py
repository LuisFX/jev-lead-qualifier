"""Catalog, compose, mounts, Connect HTTP.

TEACHING NOTE: Unmounted is Fake. An Email plugin cannot occupy Voice.
Mounted without a process credential is plugin_unready, not silent Fake.
Vendor words are zero in both oracles. INSTANTLY_SEND is unread in bindings.
⭐ ENFORCED BY: this file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from leadqualifier import server
from leadqualifier.comms import FakeComms, drain_outbound
from leadqualifier.fake_client import FakeClient
from leadqualifier.integrations import (
    EMAIL_PLUGIN,
    SMS_PLUGIN,
    VOICE_PLUGIN,
    CapabilityMismatch,
    ComposeErr,
    ComposeOk,
    Mounted,
    Unmounted,
    UnreadyComms,
    compose,
    host_catalog,
    plugin_id,
)
from leadqualifier.ledger import get_ledger
from leadqualifier.workitem import (
    ApplyOk,
    Arrive,
    CsvRow,
    ImportId,
    Judged,
    IcpVersionId,
    Queue,
    Sms,
    Unjudged,
    Copy,
    Draft,
    email_draft,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def no_vendor_keys(monkeypatch):
    monkeypatch.delenv("INSTANTLY_API_KEY", raising=False)
    monkeypatch.delenv("INSTANTLY_CAMPAIGN_ID", raising=False)
    monkeypatch.delenv("INSTANTLY_SEND", raising=False)
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_FROM_NUMBER", raising=False)


@pytest.fixture
def client():
    server.set_client(FakeClient())
    with TestClient(server.app) as c:
        yield c
    server.set_client(None)


def _warm():
    return Judged(IcpVersionId("v1"), "warm", False)


def _payload(wid: str, *, email: str | None = None, phone: str | None = None) -> dict:
    person: dict[str, str] = {"name": "Ada"}
    if email:
        person["email"] = email
    if phone:
        person["phone"] = phone
    return {
        "id": wid,
        "source": "csv_import",
        "received_at": "2026-11-18T00:00:00Z",
        "person": person,
        "company": {"name": "Analytical", "domain": "analytical.de"},
        "message": {"text": "We drown in reports."},
    }


def _arrive(wid: str, **addr: str | None) -> None:
    ledger = get_ledger()
    born = ledger.apply_command(
        wid, Arrive(CsvRow(ImportId(wid), 1)), Unjudged(), payload=_payload(wid, **addr)
    )
    assert isinstance(born, ApplyOk)


def _slot(slots: list[dict], channel: str) -> dict:
    found = [s for s in slots if s["channel"] == channel]
    assert found, f"missing slot {channel}"
    return found[0]


def test_compose_unmounted_is_fake_on_email_and_voice():
    fake = FakeComms()
    out = compose(host_catalog(), {}, fake=fake)
    assert isinstance(out, ComposeOk)
    from leadqualifier.workitem import Email, Voice

    assert out.bindings.lookup(Email()) is fake
    assert out.bindings.lookup(Voice()) is fake


def test_compose_email_plugin_on_email_leaves_voice_fake():
    fake = FakeComms()
    mounts = {"email": Mounted(plugin_id(EMAIL_PLUGIN))}
    out = compose(host_catalog(), mounts, fake=fake)
    assert isinstance(out, ComposeOk)
    from leadqualifier.workitem import Email, Voice

    assert isinstance(out.bindings.lookup(Email()), UnreadyComms)
    assert out.bindings.lookup(Voice()) is fake


def test_compose_email_plugin_on_voice_is_capability_mismatch():
    fake = FakeComms()
    mounts = {"voice": Mounted(plugin_id(EMAIL_PLUGIN))}
    out = compose(host_catalog(), mounts, fake=fake)
    assert isinstance(out, ComposeErr)
    assert isinstance(out.error, CapabilityMismatch)
    from leadqualifier.workitem import Voice

    empty = compose(host_catalog(), {}, fake=fake)
    assert isinstance(empty, ComposeOk)
    assert empty.bindings.lookup(Voice()) is fake


def test_unmount_email_returns_fake():
    fake = FakeComms()
    mounted = compose(host_catalog(), {"email": Mounted(plugin_id(EMAIL_PLUGIN))}, fake=fake)
    assert isinstance(mounted, ComposeOk)
    from leadqualifier.workitem import Email

    assert isinstance(mounted.bindings.lookup(Email()), UnreadyComms)
    cleared = compose(host_catalog(), {"email": Unmounted()}, fake=fake)
    assert isinstance(cleared, ComposeOk)
    assert cleared.bindings.lookup(Email()) is fake


def test_http_get_shape_and_voice_candidates(client):
    r = client.get("/api/integrations")
    assert r.status_code == 200
    slots = r.json()["slots"]
    assert [s["channel"] for s in slots] == [
        "email",
        "linkedin",
        "voice",
        "sms",
        "ringless_voicemail",
    ]
    email = _slot(slots, "email")
    voice = _slot(slots, "voice")
    sms = _slot(slots, "sms")
    rvm = _slot(slots, "ringless_voicemail")
    linkedin = _slot(slots, "linkedin")
    assert email["mount"]["kind"] == "unmounted"
    assert email["candidates"] == [EMAIL_PLUGIN]
    assert voice["candidates"] == [VOICE_PLUGIN]
    assert sms["candidates"] == [SMS_PLUGIN]
    assert rvm["candidates"] == []
    assert linkedin["candidates"] == []
    recv = r.json()["receive"]
    assert _slot(recv, "email")["candidates"] == [EMAIL_PLUGIN]
    assert _slot(recv, "voice")["candidates"] == []
    blob = json.dumps(r.json())
    assert "api_key" not in blob.lower()
    assert "INSTANTLY" not in blob
    assert "TWILIO" not in blob
    status = client.get("/api/status").json()
    assert "instantly" not in status
    assert status["mounts"]["email"]["kind"] == "unmounted"
    assert status["mounts"]["voice"]["kind"] == "unmounted"


def test_http_mount_unmount_and_409_mismatch(client):
    bad = client.post("/api/integrations/mount", json={"channel": "voice", "plugin_id": EMAIL_PLUGIN})
    assert bad.status_code == 409
    assert bad.json()["detail"]["refusal"] == "capability_mismatch"
    unknown = client.post("/api/integrations/mount", json={"channel": "email", "plugin_id": "no-such"})
    assert unknown.status_code == 409
    assert unknown.json()["detail"]["refusal"] == "unknown_plugin"
    ok = client.post("/api/integrations/mount", json={"channel": "email", "plugin_id": EMAIL_PLUGIN})
    assert ok.status_code == 200
    email = _slot(ok.json()["slots"], "email")
    assert email["mount"] == {"kind": "mounted", "plugin_id": EMAIL_PLUGIN}
    assert email["needs_credential"] is True
    assert email["ready"] is False
    status = client.get("/api/status").json()
    assert status["mounts"]["email"]["kind"] == "mounted"
    assert status["mounts"]["email"]["ready"] is False
    gone = client.post("/api/integrations/unmount", json={"channel": "email"})
    assert gone.status_code == 200
    assert _slot(gone.json()["slots"], "email")["mount"]["kind"] == "unmounted"
    sms_bad = client.post("/api/integrations/mount", json={"channel": "sms", "plugin_id": EMAIL_PLUGIN})
    assert sms_bad.status_code == 409
    assert sms_bad.json()["detail"]["refusal"] == "capability_mismatch"
    sms_ok = client.post("/api/integrations/mount", json={"channel": "sms", "plugin_id": SMS_PLUGIN})
    assert sms_ok.status_code == 200
    assert _slot(sms_ok.json()["slots"], "sms")["mount"] == {"kind": "mounted", "plugin_id": SMS_PLUGIN}
    voice_ok = client.post("/api/integrations/mount", json={"channel": "voice", "plugin_id": VOICE_PLUGIN})
    assert voice_ok.status_code == 200
    assert _slot(voice_ok.json()["slots"], "voice")["candidates"] == [VOICE_PLUGIN]


def test_drain_mounted_not_ready_is_plugin_unready():
    ledger = get_ledger()
    _arrive("I-unready", email="ada@secret.test")
    assert isinstance(ledger.apply_command("I-unready", Queue(email_draft()), _warm()), ApplyOk)
    fake = FakeComms()
    out = compose(host_catalog(), {"email": Mounted(plugin_id(EMAIL_PLUGIN))}, fake=fake)
    assert isinstance(out, ComposeOk)
    drained = drain_outbound(ledger, out.bindings)
    assert drained["failed"] == 1
    assert fake.calls == []
    row = ledger.get_row("I-unready")
    assert row["outbound_kind"] == "failed"
    assert row["outbound_reason"] == "plugin_unready"


def test_drain_unmounted_with_address_is_fake():
    ledger = get_ledger()
    _arrive("I-fake", email="ada@secret.test")
    assert isinstance(ledger.apply_command("I-fake", Queue(email_draft()), _warm()), ApplyOk)
    fake = FakeComms()
    out = compose(host_catalog(), {}, fake=fake)
    assert isinstance(out, ComposeOk)
    drained = drain_outbound(ledger, out.bindings)
    assert drained["dispatched"] == 1
    assert fake.calls[0]["remote_id"] == "fake-comms-1"
    row = ledger.get_row("I-fake")
    assert row["outbound_kind"] == "dispatched"
    assert row["outbound_remote_id"] == "fake-comms-1"


def test_drain_sms_mounted_not_ready_is_plugin_unready():
    ledger = get_ledger()
    _arrive("I-sms-unready", phone="+494012345")
    assert isinstance(
        ledger.apply_command("I-sms-unready", Queue(Draft(Sms(), Copy("sms ping"))), _warm()),
        ApplyOk,
    )
    fake = FakeComms()
    out = compose(host_catalog(), {"sms": Mounted(plugin_id(SMS_PLUGIN))}, fake=fake)
    assert isinstance(out, ComposeOk)
    drained = drain_outbound(ledger, out.bindings)
    assert drained["failed"] == 1
    assert fake.calls == []
    row = ledger.get_row("I-sms-unready")
    assert row["outbound_kind"] == "failed"
    assert row["outbound_reason"] == "plugin_unready"


def test_twilio_sms_mocked_post_does_not_hit_network(monkeypatch):
    from leadqualifier.twilio_sms import TwilioSms

    calls: list[str] = []

    class Resp:
        status_code = 201
        content = b'{"sid":"SM123"}'

        def json(self):
            return {"sid": "SM123"}

    def fake_post(url, **kwargs):
        calls.append(url)
        assert "Messages.json" in url
        assert kwargs["auth"][0] == "ACtest"
        return Resp()

    monkeypatch.setattr("leadqualifier.twilio_sms.httpx.post", fake_post)
    remote = TwilioSms(account_sid="ACtest", auth_token="tok", from_number="+15005550006").dispatch(
        work_item_id="x",
        channel=Sms(),
        draft=Draft(Sms(), Copy("sms ping")),
        payload={"person": {"phone": "+494012345"}},
    )
    assert remote == "SM123"
    assert calls and "Messages.json" in calls[0]


def test_twilio_voice_mocked_post_does_not_hit_network(monkeypatch):
    from leadqualifier.twilio_voice import TwilioVoice
    from leadqualifier.workitem import Voice, Calendar

    calls: list[str] = []

    class Resp:
        status_code = 201
        content = b'{"sid":"CA123"}'

        def json(self):
            return {"sid": "CA123"}

    def fake_post(url, **kwargs):
        calls.append(url)
        assert "Calls.json" in url
        assert "<Say>" in kwargs["data"]["Twiml"]
        return Resp()

    monkeypatch.setattr("leadqualifier.twilio_voice.httpx.post", fake_post)
    remote = TwilioVoice(account_sid="ACtest", auth_token="tok", from_number="+15005550006").dispatch(
        work_item_id="x",
        channel=Voice(),
        draft=Draft(Voice(), Calendar(("Tue", "Thu"))),
        payload={"person": {"phone": "+494012345"}},
    )
    assert remote == "CA123"
    assert calls and "Calls.json" in calls[0]


def test_oracles_do_not_name_instantly():
    integ = (ROOT / "leadqualifier" / "integrations.fsx").read_text(encoding="utf-8")
    work = (ROOT / "leadqualifier" / "workitem.fsx").read_text(encoding="utf-8")
    adapter = (ROOT / "leadqualifier" / "instantly.py").read_text(encoding="utf-8")
    bindings = (ROOT / "leadqualifier" / "bindings.py").read_text(encoding="utf-8")
    comms = (ROOT / "leadqualifier" / "comms.py").read_text(encoding="utf-8")
    inbound = (ROOT / "leadqualifier" / "inbound.py").read_text(encoding="utf-8")
    assert "Voice" in comms
    assert "Instantly" not in integ
    assert "Instantly" not in work
    assert "Voice" not in adapter
    assert "class InstantlyEmail" in adapter
    assert "INSTANTLY_SEND" not in bindings
    assert "Instantly" not in inbound
