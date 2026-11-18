"""ts-012 outbox, ts-013 mapping. Live HubSpot is skipped without HUBSPOT_WRITE.

TEACHING NOTE: FakeWriter proves the outbox, not HubSpot. A second HandOff must
not call the writer. Live property write is ts-013's smoke, on a test contact.
"""

from __future__ import annotations

from leadqualifier.hubspot import FakeWriter, properties_from_result
from leadqualifier.ledger import get_ledger
from leadqualifier.leads import load_leads
from leadqualifier.relay import drain_once
from leadqualifier.workitem import ApplyOk, Err, HandOff, IcpVersionId, Judged, Unjudged


def _hot():
    return Judged(IcpVersionId("v1"), "hot", False)


def test_handoff_then_second_is_already_handed_off():
    load_leads()
    ledger = get_ledger()
    first = ledger.apply_command("L001", HandOff(), _hot())
    assert isinstance(first, ApplyOk)
    assert ledger.get_row("L001")["relay_kind"] == "pending"
    writer = FakeWriter()
    result = {
        "tier": "hot",
        "fit": 0.8,
        "intent": 0.7,
        "route": {"label": "Founder call"},
        "primary_pain": "manual_reporting",
        "next_action": {"label": "Book a call"},
        "icp_version_id": "v1",
        "why": ["hot"],
    }
    out = drain_once(ledger, writer, {"L001": result})
    assert out["delivered"] == 1 and writer.calls[0]["properties"]["tier"] == "hot"
    assert ledger.get_row("L001")["relay_kind"] == "delivered"
    second = ledger.apply_command("L001", HandOff(), _hot())
    assert isinstance(second, Err) and second.error.kind == "already_handed_off"
    assert len(writer.calls) == 1


def test_property_map():
    props = properties_from_result(
        {"tier": "hot", "fit": 0.81, "intent": 0.6, "route": {"label": "Call"}, "primary_pain": "p", "next_action": {"label": "Book"}}
    )
    assert props == {
        "tier": "hot",
        "route": "Call",
        "fit": "0.81",
        "intent": "0.6",
        "primary_pain": "p",
        "next_action": "Book",
    }
