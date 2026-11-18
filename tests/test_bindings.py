"""Bindings: lookup by draft.channel. Incomplete map is channel_unbound.

TEACHING NOTE: production default_bindings is total Fake. channel_unbound is a
missing key (tests construct it). Swap Email leaves Voice on Fake.
⭐ ENFORCED BY: this file. InstantlyEmail source names Email only; control is
`comms.py` still containing Voice so a zero is not a blind instrument.
"""

from __future__ import annotations

from pathlib import Path

from leadqualifier.comms import Bindings, FakeComms, drain_outbound, fake_bindings
from leadqualifier.ledger import get_ledger
from leadqualifier.workitem import (
    ApplyOk,
    Arrive,
    Copy,
    CsvRow,
    Draft,
    HandOff,
    IcpVersionId,
    ImportId,
    Judged,
    Queue,
    Sms,
    Unjudged,
    email_draft,
    voice_draft,
)

ROOT = Path(__file__).resolve().parents[1]


def _warm():
    return Judged(IcpVersionId("v1"), "warm", False)


def _hot():
    return Judged(IcpVersionId("v1"), "hot", False)


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


class EmailSpy:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def dispatch(self, *, work_item_id: str, channel, draft, payload) -> str:
        self.calls.append(channel.kind)
        return "spy-email"


def test_fake_drain_email_voice_sms_records_distinct_channels():
    ledger = get_ledger()
    _arrive("B-mail", email="ada@secret.test")
    _arrive("B-voice", phone="+494012345")
    _arrive("B-sms", phone="+494055555")
    assert isinstance(ledger.apply_command("B-mail", Queue(email_draft()), _warm()), ApplyOk)
    assert isinstance(ledger.apply_command("B-voice", HandOff(voice_draft()), _hot()), ApplyOk)
    assert isinstance(
        ledger.apply_command("B-sms", Queue(Draft(Sms(), Copy("sms ping"))), _warm()), ApplyOk
    )
    fake = FakeComms()
    out = drain_outbound(ledger, fake_bindings(fake))
    assert out["dispatched"] == 3
    by_id = {c["work_item_id"]: c for c in fake.calls}
    assert by_id["B-mail"]["channel"] == "email" and by_id["B-mail"]["address"] == "ada@secret.test"
    assert by_id["B-voice"]["channel"] == "voice" and by_id["B-voice"]["address"] == "+494012345"
    assert by_id["B-sms"]["channel"] == "sms" and by_id["B-sms"]["address"] == "+494055555"


def test_incomplete_map_sms_is_channel_unbound():
    ledger = get_ledger()
    _arrive("B-unbound", phone="+4940999")
    assert isinstance(
        ledger.apply_command("B-unbound", Queue(Draft(Sms(), Copy("sms ping"))), _warm()), ApplyOk
    )
    fake = FakeComms()
    out = drain_outbound(ledger, Bindings({"email": fake}))
    assert out["failed"] == 1
    assert fake.calls == []
    row = ledger.get_row("B-unbound")
    assert row["outbound_kind"] == "failed"
    assert row["outbound_reason"] == "channel_unbound"


def test_with_email_leaves_voice_on_fake():
    ledger = get_ledger()
    _arrive("B-swap-v", phone="+494012345")
    _arrive("B-swap-e", email="ada@secret.test")
    assert isinstance(ledger.apply_command("B-swap-v", HandOff(voice_draft()), _hot()), ApplyOk)
    assert isinstance(ledger.apply_command("B-swap-e", Queue(email_draft()), _warm()), ApplyOk)
    fake = FakeComms()
    spy = EmailSpy()
    bindings = fake_bindings(fake).with_email(spy)
    out = drain_outbound(ledger, bindings)
    assert out["dispatched"] == 2
    assert fake.calls[0]["channel"] == "voice"
    assert spy.calls == ["email"]
    assert all(c["channel"] != "email" for c in fake.calls)


def test_email_adapter_source_does_not_name_voice():
    instantly = (ROOT / "leadqualifier" / "instantly.py").read_text(encoding="utf-8")
    comms = (ROOT / "leadqualifier" / "comms.py").read_text(encoding="utf-8")
    assert "Voice" in comms
    assert "Voice" not in instantly
