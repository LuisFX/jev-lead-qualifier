# Demo script — First Read for Lanternfield Automation (about 4 minutes, 6 beats)

Everything is driven by the **Demo** button in the top bar: a panel with six beats, one **Run** button each, a result line in monospace and the buyer caption to say out loud. Progress dots show what you have covered; **Reset demo** restores the default ICP (cached answers are kept, so nothing gets slower).

**Before recording**

```bash
cd lead-qualifier && ./run.sh serve          # http://127.0.0.1:8780   (add ?demo=1 to open the panel on load)
```

Window ≥ 1400 px wide. Light or dark — the toggle is in the top bar. If you want the streaming counters to start from zero, press **Re-run fresh** once before recording, or start straight with beat (a), which always re-asks Jev.

Frame the story first (10 s): "Lanternfield Automation sells automation to agencies and coaches. Their inbox is website forms, cold-email replies and LinkedIn exports. Nobody reads them in time. This is the product that reads first."

---

### a. Run 65 leads live (30 s)

Action: **Run**. Talk over the stream: the tier board fills left to right, the counters show requests, latency, cost, "needs a human". Result line: `65 leads · 65 requests · ~6 s · $0.014 · $0.22 per 1,000 · 7 flagged · tier accuracy 100 % vs gold`.

> **Buyer:** Every inbound is qualified before anyone on your team opens it. Sixty-five leads, thirty-two questions each, six seconds, one and a half cents. Six SDR minutes per lead, back.

Point at the **Value for the buyer** card: hours saved, share routed without a human, vendor pitches kept away, duplicates handed to their owner.

### b. The vague-but-hot inbound (35 s)

Action: **Run** — opens Lindqvist & Co: *"Hi — we're drowning in reporting for 14 clients … Do you do this? Could we talk this week?"* No budget field, no timeline field. The pain sentence is highlighted in the pain's colour, the call-request sentence is underlined; the card says Hot, fit 1.00, intent ~0.78, Founder call with two slots.

> **Buyer:** Intent is read from meaning, not from form fields. Jev pointed at the exact sentences — the reasons are on the page, not in a black box.

Scroll to the quadrant and the contributions: fit and intent are weighted sums you can read.

### c. Vendor pitch and student, out (30 s)

Action: **Run** — opens ScaleSignal ("partnership … 20 % off … 15 minutes this week?") then, after a beat, the thesis interview request. Both land in Disqualified with named reasons: vendor pitch 0.99 / competitor 0.93; student 0.98. The next action is a polite decline **drafted**, never sent.

> **Buyer:** Both read well. Both would have cost an SDR ten minutes. Your team's time is protected, and nobody gets an automated brush-off.

### d. Duplicate of a CRM account (25 s)

Action: **Run** — Jonas from Hafenblick Digital writes in again. Code shortlisted the CRM account (same domain), Jev confirmed it is the same organisation (P 0.94, customer). Route: account owner Lena Berg, no sequence.

> **Buyer:** No double outreach, no second record in the CRM. Existing customers go to the person who knows them.

Optional: open Kontor Süd (L065) from the Warm column — shortlisted against Kontor Nord by code, rejected by Jev with P(none) 1.00.

### e. Edit the ICP, tiers re-shuffle (60 s)

Action: **Run** — the ICP page opens. First the minimum revenue band is raised to €30k/month: the **Live re-scoring** card shows three leads move from Hot/Warm to Disqualified with "below minimum revenue band" — from cache, zero API calls. Then a new pain, *client churn*, is added and saved: the card "What a run would ask" says 127 questions; the run asks only those (~760 tokens per lead instead of ~5,000, about 5 s, $0.002) and two leads now carry the churn pain.

> **Buyer:** Your ICP in plain English. Move a threshold and every lead re-scores in milliseconds. Add a question and you pay only for the delta — no retraining, no data-science ticket.

Show the preset dropdown: *B2B SaaS founders*, *E-commerce brands* — same build, different client.

### f. Explore: the pain heatmap (30 s)

Action: **Run** — the Explore page. The scatter shows every lead in fit × intent; the heatmap shows which pains the Hot leads name: `4 of 10 Hot leads name manual reporting`.

> **Buyer:** Your best leads tell you what to say in your ads and on the landing page. That is positioning intel you did not have to run a survey for.

### Close (10 s)

> "One request per lead, questions written in your language, calibrated probabilities, decisions in code you can read. Same build for agencies, SaaS founders and e-commerce brands — only the ICP changes."

---

**Accuracy tab** (optional, 20 s): 65 gold-labelled leads, tier accuracy on the recorded run 100 %, split into auto-routed and flagged-for-a-human. Say honestly that the dataset and thresholds were tuned together and that repeat runs move about one lead near the Warm/Nurture line — the flagged bucket exists for exactly that.

**Fallbacks**

- `FIRSTREAD_FAKE=1 ./run.sh serve` runs the whole demo on a deterministic offline stand-in if the API is down (the status pill says so; the numbers are not meaningful).
- URL shortcuts: `/?demo=1`, `/?run=fresh`, `/?lead=L001`, `/#explore`, `/?theme=light`.
- CLI equivalent of beat (a): `./run.sh score --force`.
- Screenshots of every beat's screen are in `reports/ui/` (`demo-panel-*`, `pipeline-streaming-*`, `lead-hot-*`, `lead-vendor-*`, `lead-existing-*`, `icp-live-*`, `explore-*`).
