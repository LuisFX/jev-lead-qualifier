"""InboundMatch: vendor-blind hint, then RecordReply. Paste stays a second door.

TEACHING NOTE: 0 or 2+ hits are UnknownSender. Paste of an unknown id is 404;
an unknown inbound hint is 409 unknown_sender. `decide` never sees the hint.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from leadqualifier import server
from leadqualifier.fake_client import FakeClient
from leadqualifier.inbound import ByEmail, ByPhone, ByWorkItem, Matched, UnknownSender, match_inbound
from leadqualifier.ledger import get_ledger
from leadqualifier.workitem import ApplyOk, Arrive, CsvRow, ImportId, Unjudged

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client():
    server.set_client(FakeClient())
    with TestClient(server.app) as c:
        yield c
    server.set_client(None)


def _payload(wid: str, *, email: str | None = None, phone: str | None = None, text: str = "We drown in reports.") -> dict:
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
        "message": {"text": text},
    }


def _arrive(wid: str, **addr: str | None) -> None:
    ledger = get_ledger()
    born = ledger.apply_command(
        wid, Arrive(CsvRow(ImportId(wid), 1)), Unjudged(), payload=_payload(wid, **addr)
    )
    assert isinstance(born, ApplyOk)


def test_match_by_work_item_known_and_unknown():
    _arrive("IN-id")
    ledger = get_ledger()
    found = match_inbound(ledger, ByWorkItem("IN-id"))
    assert isinstance(found, Matched) and found.work_item_id == "IN-id"
    miss = match_inbound(ledger, ByWorkItem("no-such"))
    assert isinstance(miss, UnknownSender)
    assert ledger.get_row("no-such") is None


def test_match_by_email_unique_duplicate_blank():
    _arrive("IN-mail-a", email="ada@secret.test")
    _arrive("IN-mail-b", email="other@secret.test")
    ledger = get_ledger()
    found = match_inbound(ledger, ByEmail("Ada@secret.test"))
    assert isinstance(found, Matched) and found.work_item_id == "IN-mail-a"
    blank = match_inbound(ledger, ByEmail("   "))
    assert isinstance(blank, UnknownSender)
    _arrive("IN-mail-dup", email="ada@secret.test")
    dup = match_inbound(ledger, ByEmail("ada@secret.test"))
    assert isinstance(dup, UnknownSender)


def test_match_by_phone_unique():
    _arrive("IN-phone", phone="+494012345")
    found = match_inbound(get_ledger(), ByPhone(" +494012345 "))
    assert isinstance(found, Matched) and found.work_item_id == "IN-phone"
    miss = match_inbound(get_ledger(), ByPhone("+490000"))
    assert isinstance(miss, UnknownSender)


def test_http_inbound_unique_email_folds_body(client):
    csv = "name,email,company,message\nAda,ada@secret.test,Analytical,We drown in reports.\n"
    imported = client.post("/api/imports", json={"csv": csv, "import_id": "inb-1"}).json()
    wid = imported["inserted"][0]
    r = client.post(
        "/api/inbound",
        json={"hint": {"kind": "email", "email": "ada@secret.test"}, "text": "Tuesday works"},
    )
    assert r.status_code == 200
    lead = r.json()["lead"]
    assert lead["id"] == wid
    assert lead["disposition"] == "unreviewed"
    assert lead["message"]["text"] == "Tuesday works"
    assert lead["message"]["prior"] == "We drown in reports."


def test_http_inbound_unknown_email_is_409(client):
    r = client.post(
        "/api/inbound",
        json={"hint": {"kind": "email", "email": "nobody@secret.test"}, "text": "hello"},
    )
    assert r.status_code == 409 and r.json()["detail"]["refusal"] == "unknown_sender"


def test_http_inbound_matched_whitespace_is_empty_reply(client):
    csv = "name,email,company,message\nKai,kai@secret.test,Berg,Hi\n"
    client.post("/api/imports", json={"csv": csv, "import_id": "inb-empty"})
    r = client.post(
        "/api/inbound",
        json={"hint": {"kind": "email", "email": "kai@secret.test"}, "text": "  "},
    )
    assert r.status_code == 409 and r.json()["detail"]["refusal"] == "empty_reply"


def test_paste_empty_still_409_and_body_still_200(client):
    empty = client.post("/api/leads/L001/reply", json={"text": "  "})
    assert empty.status_code == 409 and empty.json()["detail"]["refusal"] == "empty_reply"
    ok = client.post("/api/leads/L001/reply", json={"text": "we booked Tuesday"})
    assert ok.status_code == 200
    assert ok.json()["lead"]["disposition"] == "unreviewed"
    assert ok.json()["lead"]["message"]["text"] == "we booked Tuesday"


def test_inbound_source_does_not_name_vendor_or_external_id():
    inbound = (ROOT / "leadqualifier" / "inbound.py").read_text(encoding="utf-8")
    comms = (ROOT / "leadqualifier" / "comms.py").read_text(encoding="utf-8")
    assert "Voice" in comms
    assert "Instantly" not in inbound
    assert "externalId" not in inbound


def test_receive_email_unmounted_is_404(client):
    r = client.post("/api/receive/email", json={"event_type": "reply_received", "lead_email": "a@b.test", "reply_text": "hi"})
    assert r.status_code == 404


def test_receive_email_other_event_is_204(client):
    mounted = client.post(
        "/api/integrations/receive/mount", json={"channel": "email", "plugin_id": "email-plugin"}
    )
    assert mounted.status_code == 200
    r = client.post("/api/receive/email", json={"event_type": "email_opened", "lead_email": "a@b.test"})
    assert r.status_code == 204


def test_receive_email_fixture_folds_like_paste(client):
    csv = "name,email,company,message\nAda,ada@secret.test,Analytical,We drown in reports.\n"
    imported = client.post("/api/imports", json={"csv": csv, "import_id": "recv-1"}).json()
    wid = imported["inserted"][0]
    mounted = client.post(
        "/api/integrations/receive/mount", json={"channel": "email", "plugin_id": "email-plugin"}
    )
    assert mounted.status_code == 200
    r = client.post(
        "/api/receive/email",
        json={
            "event_type": "reply_received",
            "lead_email": "ada@secret.test",
            "reply_text": "Tuesday works",
        },
    )
    assert r.status_code == 200
    lead = r.json()["lead"]
    assert lead["id"] == wid
    assert lead["disposition"] == "unreviewed"
    assert lead["message"]["text"] == "Tuesday works"
    assert lead["message"]["prior"] == "We drown in reports."


def test_receive_email_unknown_is_409(client):
    mounted = client.post(
        "/api/integrations/receive/mount", json={"channel": "email", "plugin_id": "email-plugin"}
    )
    assert mounted.status_code == 200
    r = client.post(
        "/api/receive/email",
        json={"event_type": "reply_received", "lead_email": "nobody@secret.test", "reply_text": "hello"},
    )
    assert r.status_code == 409 and r.json()["detail"]["refusal"] == "unknown_sender"


def test_receive_voice_plugin_on_email_in_is_409(client):
    r = client.post(
        "/api/integrations/receive/mount", json={"channel": "email", "plugin_id": "voice-plugin"}
    )
    assert r.status_code == 409 and r.json()["detail"]["refusal"] == "capability_mismatch"


def test_parse_instantly_inbound_maps_reply_received():
    from leadqualifier.instantly_inbound import Ignore, ParsedReply, parse_instantly_inbound

    parsed = parse_instantly_inbound(
        {"event_type": "reply_received", "lead_email": "ada@secret.test", "reply_text": "Tuesday works"}
    )
    assert isinstance(parsed, ParsedReply)
    assert parsed.hint.email == "ada@secret.test"
    assert parsed.body == "Tuesday works"
    assert isinstance(parse_instantly_inbound({"event_type": "email_sent"}), Ignore)


def test_arrival_has_no_reply_case():
    src = (ROOT / "leadqualifier" / "workitem.fsx").read_text(encoding="utf-8")
    start = src.index("type Arrival =")
    end = src.index("type Tier =")
    block = src[start:end]
    assert "ApolloPerson" in block and "CsvRow" in block
    assert "Reply" not in block
