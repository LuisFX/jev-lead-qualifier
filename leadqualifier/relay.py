"""Outbox worker: pending HubSpot writes become MarkDelivered or MarkFailed.

TEACHING NOTE: HandOff of Hot already emits RelayPending (L14). This loop is
the other half: HubSpot `Writer` and `Bindings` drain. Idempotent on work
item + ICP version: a second HandOff is `already_handed_off` and never
reaches here. The worker is a thread in the same process, not a second service.

⭐ ENFORCED BY: `tests/test_relay.py`.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

from .bindings import get_bindings
from .comms import Bindings, drain_outbound
from .hubspot import FakeWriter, HubSpotWriter, Writer
from .leads import lead_from_payload
from .workitem import MarkDelivered, MarkFailed, Unjudged

log = logging.getLogger("firstread.relay")


def drain_once(ledger, writer: Writer, results_by_id: dict[str, dict[str, Any]] | None = None) -> dict[str, int]:
    delivered = failed = 0
    for row in ledger.list_pending_relay():
        wid = row["id"]
        payload = json.loads(row["payload_json"])
        result = (results_by_id or {}).get(wid)
        if result is None:
            from .pipeline import Qualifier
            from . import icp as icp_mod
            from .leads import load_crm, load_playbook

            q = Qualifier(icp_mod.load(), load_crm(), load_playbook(), client=None, cache=ledger, icp_version_id=icp_mod.live_version_id())
            result = q.rescore(lead_from_payload(payload))
        if result is None:
            ledger.apply_command(wid, MarkFailed("no judgement to write"), Unjudged())
            failed += 1
            continue
        existing = result.get("tier") == "existing" or bool(result.get("existing_account"))
        try:
            remote = writer.write(
                work_item_id=wid,
                icp_version_id=str(result.get("icp_version_id") or icp_version_of(ledger)),
                result=result,
                payload=payload,
                existing_account=existing,
            )
            out = ledger.apply_command(wid, MarkDelivered(remote), Unjudged())
            if getattr(out, "kind", None) == "error":
                log.warning("mark delivered refused id=%s %s", wid, out.error.kind)
                failed += 1
            else:
                delivered += 1
        except Exception as exc:
            ledger.apply_command(wid, MarkFailed(f"{type(exc).__name__}: {exc}"[:240]), Unjudged())
            failed += 1
            log.warning("relay failed id=%s: %s", wid, exc)
    return {"delivered": delivered, "failed": failed}


def icp_version_of(ledger) -> str:
    return ledger.live_icp_version_id() or "unknown"


def default_writer() -> Writer:
    from . import config

    if config.hubspot_write_enabled():
        return HubSpotWriter()
    return FakeWriter()


class RelayLoop:
    def __init__(self, ledger, writer: Writer | None = None, bindings: Bindings | None = None, interval_s: float = 2.0):
        self.ledger = ledger
        self.writer = writer or default_writer()
        self.bindings = bindings if bindings is not None else get_bindings()
        self.interval_s = interval_s
        self.stop = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.thread is not None:
            return
        self.thread = threading.Thread(target=self._run, name="relay", daemon=True)
        self.thread.start()

    def _run(self) -> None:
        while not self.stop.wait(self.interval_s):
            try:
                drain_once(self.ledger, self.writer)
                drain_outbound(self.ledger, self.bindings)
            except Exception as exc:
                log.warning("relay loop: %s", exc)
                time.sleep(self.interval_s)
