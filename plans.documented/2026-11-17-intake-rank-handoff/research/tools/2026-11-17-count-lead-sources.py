"""Count demo-lead sources, CRM accounts, and ICP presets. Run from the repo root.

    python3 plans.documented/2026-11-17-intake-rank-handoff/research/tools/2026-11-17-count-lead-sources.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
leads = ROOT / "data" / "leads"
counts: Counter[str] = Counter()
for path in sorted(leads.glob("*.json")):
    item = json.loads(path.read_text(encoding="utf-8"))
    counts[str(item.get("source", "?"))] += 1

crm = json.loads((ROOT / "data" / "crm.json").read_text(encoding="utf-8"))
presets = sorted(p.stem for p in (ROOT / "data" / "icp_presets").glob("*.json"))

print(f"leads {sum(counts.values())}")
for source, n in sorted(counts.items()):
    print(f"{n:3} {source}")
print(f"crm_accounts {len(crm['accounts'])}")
print("presets " + " ".join(presets))
