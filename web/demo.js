/* First Read — guided demo panel: six beats, one click each, with the buyer caption. */
(() => {
  const FR = window.FR;
  const { el, esc, usd, pct, title, toast, sleep, state, api } = FR;
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));

  const NEW_PAIN = { id: "client_churn", description: "Clients leave or threaten to leave because results are not visible, reports are late or communication is slow", weight: 0.8 };
  const RAISED_BAND = "30k_100k";

  const leadLine = (d) => {
    const r = d.result; if (!r) return "not scored";
    const ev = Object.entries(r.evidence.pains).map(([p, e]) => `${title(p)}→${e.sentence}`).join(", ");
    return `${r.tier.toUpperCase()} · fit ${r.fit.toFixed(2)} · intent ${r.intent.toFixed(2)}${ev ? ` · pain evidence ${ev}` : ""}${r.evidence.intent ? ` · intent evidence ${r.evidence.intent.sentence}` : ""} · ${r.route.label}`;
  };

  const BEATS = [
    { id: "a", title: "Run 65 leads live", why: "<b>Every inbound is qualified before a human reads it.</b> One request per lead, ~32 questions each, four in parallel: the whole inbox in seconds for a few cents. Watch the tier board fill and the cost counter stay near zero.",
      run: async () => {
        const d = await FR.run(true);
        if (!d) return "failed";
        const t = d.totals;
        return `${t.leads} leads · ${t.requests} requests · ${t.elapsed_s} s · ${usd(t.cost_usd)} (${t.input_tokens.toLocaleString()} tokens) · $${t.cost_per_1000_usd.toFixed(2)} per 1,000 · ${t.needs_review} flagged for a human${d.metrics ? ` · tier accuracy ${pct(d.metrics.tier_accuracy)} vs gold` : ""}`;
      } },
    { id: "b", title: "The vague-but-hot inbound", why: "“We're drowning in reporting for 14 clients, do you do this?” No form field says <i>budget</i> or <i>timeline</i>. <b>Intent is read from meaning, not from fields</b>: the pain sentence and the call-request sentence are highlighted because Jev pointed at them.",
      run: async () => { const d = await ensureScored("L001"); await sleep(400); return leadLine(d); } },
    { id: "c", title: "Vendor pitch and student, out", why: "A polished partnership pitch and a friendly thesis request both read well. <b>SDR time is protected</b>: each is disqualified with a named reason and a decline template that is drafted, never sent.",
      run: async () => {
        const a = await ensureScored("L047"); await sleep(2600);
        const b = await ensureScored("L048");
        const line = (d) => `${state.leadsById[d.lead.id].company_name}: ${d.result.tier} — ${d.result.disqualifiers.map((x) => `${x.label} ${x.p.toFixed(2)}`).join(", ")}`;
        return `${line(a)}\n${line(b)}`;
      }, warn: true },
    { id: "d", title: "Duplicate of a CRM account", why: "Jonas from Hafenblick writes in again. Code shortlists similar CRM accounts, Jev decides whether it is the same organisation. <b>No double outreach</b>: the message goes to the account owner, not into a sequence.",
      run: async () => {
        const d = await ensureScored("L060"); const r = d.result;
        return r.existing_account ? `${r.tier} · same as ${r.existing_account.name} (P ${r.existing_account.p.toFixed(2)}) · ${r.existing_account.status} · owner ${r.existing_account.owner}` : `not matched: ${r.tier}`;
      } },
    { id: "e", title: "Edit the ICP, tiers re-shuffle", why: "<b>The ICP in plain English, changes in seconds.</b> Raise the minimum revenue band: leads that stated €15–22k a month drop out instantly from cache, zero API calls. Add a pain, “client churn”: only its two questions are asked on the next run, everything else is reused.",
      run: async () => {
        FR.showPage("icp"); await FR.loadICP(true);
        if (!Object.keys(state.results).length) return "run the pipeline first (beat a)";
        const original = state.icp.min_revenue_band;
        state.icpDraft.min_revenue_band = RAISED_BAND; FR.renderICPForm(); await FR.refreshLive(true);
        const moved = (state.liveMoves || []).map((r) => `${state.leadsById[r.lead_id]?.company_name}: ${state.results[r.lead_id].tier}→${r.tier}`);
        toast(`Minimum revenue raised to 30k/month — ${moved.length} leads changed tier, 0 API calls`);
        await sleep(3200);
        const hadPain = !!state.icpDraft.pains[NEW_PAIN.id];
        if (!hadPain) FR.addItem("pains", NEW_PAIN.id, NEW_PAIN.description, true, NEW_PAIN.weight);
        state.icpDraft.min_revenue_band = original;  // keep the band change as a preview; persist only the new pain
        FR.renderICPForm(); await FR.refreshLive(true);
        document.querySelector("#sec-pains")?.scrollIntoView({ block: "nearest", behavior: "smooth" });
        await sleep(1200);
        const saved = await FR.saveICP();
        const toAsk = saved?.stale?.questions_to_ask ?? 0;
        const runRes = toAsk ? await FR.run(false) : null;
        FR.showPage("icp"); await FR.loadICP(true);
        const withPain = Object.values(state.results).filter((r) => (r.components.pains.scores[NEW_PAIN.id] || 0) >= state.icp.thresholds.pain_p);
        const perLead = runRes ? Math.round(runRes.totals.input_tokens / Math.max(1, runRes.totals.requests)) : 0;
        return `revenue gate 30k: ${moved.length} moved (${moved.slice(0, 3).join("; ")}) · 0 calls\nadded pain “${title(NEW_PAIN.id)}”: ${toAsk} questions re-asked${runRes ? ` in ${runRes.totals.elapsed_s} s for ${usd(runRes.totals.cost_usd)} (${perLead} tokens/lead instead of ~5,000)` : ""} · ${withPain.length} leads now carry it`;
      } },
    { id: "f", title: "Explore: the pain heatmap", why: "Which problems do the <i>Hot</i> leads name? <b>Your best leads tell you what to say in your ads.</b> Filter by industry or persona and the scatter shows where the pipeline is thin.",
      run: async () => { FR.showPage("explore"); await sleep(500); FR.renderExplore(); const h = state.heatTop; return h ? `top pain among Hot leads: ${title(h.pain)} (${h.hot} of ${h.hotN}) · ${Object.keys(state.results).length} leads plotted` : "no results yet"; } },
  ];

  async function ensureScored(id) {
    let d = await FR.openLead(id, true);
    if (!d.result) { await api(`/api/score/${id}`, { method: "POST" }); await FR.loadResults(); d = await FR.openLead(id, true); }
    return d;
  }

  const demo = { current: -1, done: new Set(), running: false };
  function renderBeats() {
    const list = $("#beats"); list.innerHTML = "";
    BEATS.forEach((b, i) => {
      const li = el("li", { class: "beat" + (i === demo.current ? " current" : "") + (demo.done.has(i) ? " done" : "") + (demo.running && i === demo.current ? " running" : ""), "data-i": i });
      li.append(el("div", { class: "beat-top" }, el("span", { class: "beat-num" }, demo.done.has(i) ? "✓" : b.id), el("span", { class: "beat-title" }, b.title), el("button", { class: "btn small" + (i === demo.current ? " primary" : ""), onclick: () => runBeat(i), disabled: demo.running ? "" : null }, "Run")));
      li.append(el("div", { class: "beat-why", html: `<span class="muted">Why this matters to the buyer —</span> ${b.why}` }));
      if (b.result) li.append(el("div", { class: "beat-result" + (b.warn ? " warn" : "") }, b.result));
      list.append(li);
    });
    const dots = $("#demo-dots"); dots.innerHTML = "";
    BEATS.forEach((_, i) => dots.append(el("span", { class: "dot" + (demo.done.has(i) ? " done" : "") + (i === demo.current ? " current" : "") })));
    const next = nextBeatIndex();
    $("#demo-next").textContent = next === null ? "All beats done" : `${demo.current < 0 ? "Start" : "Next"}: ${BEATS[next].id}) ${BEATS[next].title}`;
    $("#demo-next").disabled = demo.running || next === null;
    $("#demo-meta").textContent = `${demo.done.size} / ${BEATS.length}`;
  }
  const nextBeatIndex = () => { for (let i = demo.current + 1; i < BEATS.length; i++) if (!demo.done.has(i)) return i; for (let i = 0; i < BEATS.length; i++) if (!demo.done.has(i)) return i; return null; };
  async function runBeat(i) {
    if (demo.running) return;
    demo.running = true; demo.current = i; BEATS[i].result = "running…"; renderBeats();
    $$(".beat")[i]?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    try { BEATS[i].result = await BEATS[i].run(); demo.done.add(i); }
    catch (e) { BEATS[i].result = `failed: ${e.message}`; toast(e.message, true); }
    demo.running = false; renderBeats();
  }
  function openDemo(open) {
    const panel = $("#demo-panel"), btn = $("#btn-demo");
    panel.classList.toggle("open", open); panel.setAttribute("aria-hidden", String(!open));
    btn.setAttribute("aria-expanded", String(open)); document.body.classList.toggle("demo-open", open);
    if (open) renderBeats();
  }
  $("#btn-demo").addEventListener("click", () => openDemo(!$("#demo-panel").classList.contains("open")));
  $("#demo-close").addEventListener("click", () => openDemo(false));
  $("#demo-next").addEventListener("click", () => { const n = nextBeatIndex(); if (n !== null) runBeat(n); });
  $("#demo-reset").addEventListener("click", async () => {
    if (demo.running) return;
    await api("/api/icp/reset", { method: "POST" });
    demo.current = -1; demo.done.clear(); BEATS.forEach((b) => delete b.result);
    Object.assign(FR.session, { cost: 0, requests: 0, latencies: [] }); state.lastRun = null;
    await FR.loadStatus(); await FR.loadResults(); await FR.loadICP(true); FR.showPage("pipeline"); renderBeats();
    toast("Demo reset — default ICP restored; cached answers kept");
  });
  Object.assign(FR, { openDemo, runBeat, BEATS, demo });
})();
