"""CLI: `python -m leadqualifier.cli score` (real Jev, prints tier accuracy) · `questions` (dump the set).

TEACHING NOTE: the CLI is a host. It loads leads from the ledger and answers
through the same `Qualifier` the HTTP app uses. `--no-cache` skips the ledger;
it does not delete rows.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import config, icp as icp_mod
from . import constants as C
from .ledger import get_ledger
from .leads import load_crm, load_gold, load_leads, load_playbook
from .metrics import compute_metrics, format_table
from .pipeline import Qualifier, run_totals


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="firstread")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score")
    s.add_argument("--force", action="store_true", help="ignore the cache")
    s.add_argument("--no-cache", action="store_true", help="do not read or write data/cache")
    s.add_argument("--workers", type=int, default=config.workers())
    s.add_argument("--out", default=None, help="write results JSON here")
    q = sub.add_parser("questions")
    q.add_argument("--lead", default=None)
    a = ap.parse_args(argv)

    icp = icp_mod.load()
    leads = load_leads()
    if a.cmd == "questions":
        lead = next((l for l in leads if l.id == a.lead), None) if a.lead else next(l for l in leads if l.shape == "message")
        qs, _ = Qualifier(icp, load_crm(), load_playbook(), client=None, cache=None).questions_for(lead)
        print(json.dumps(qs, indent=2, ensure_ascii=False))
        return 0

    cache = None if a.no_cache else get_ledger()
    qual = Qualifier(icp, load_crm(), load_playbook(), cache=cache)
    results = qual.score_many(leads, workers=a.workers, use_cache=not a.force,
                              on_result=lambda r: print(f"  {r['lead_id']}  {r['tier']:<10} fit {r['fit']:.2f} intent {r['intent']:.2f}  "
                                                        f"{r['meta']['n_asked']:>2} asked  {r['meta']['latency_ms']:>5} ms", file=sys.stderr))
    totals = run_totals(results, len(leads) - len(results), 0.0)
    print(json.dumps({k: v for k, v in totals.items() if k != "elapsed_s"}, indent=2))
    gold = load_gold()
    if gold and icp["id"] == config.DEFAULT_PRESET:
        print(format_table(compute_metrics(results, gold)))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump({"results": results, "totals": totals}, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
