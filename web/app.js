/* First Read — single-page UI. Plain JS, no build step.

   TEACHING NOTE: Elmish shape in the host — `state` is the Model; clicks send
   commands (`api(...)`) rather than mutating disposition in the page. Location
   is the hash: `#lead/{id}`, `#review`. Mode is Viewing | Reviewing. Contact
   is whatever the API derived (`contactOf`); the page never stores an email.
   ⭐ ENFORCED BY: the lead/review API. 🔴 UNENFORCED: nothing typechecks this file.
*/
(() => {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const el = (tag, attrs = {}, ...children) => {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "class") node.className = v;
      else if (k === "html") node.innerHTML = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else if (v !== null && v !== undefined && v !== false) node.setAttribute(k, v === true ? "" : v);
    }
    for (const c of children.flat()) if (c !== null && c !== undefined && c !== false) node.append(c.nodeType ? c : document.createTextNode(String(c)));
    return node;
  };
  const svgel = (tag, attrs = {}, ...children) => {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [k, v] of Object.entries(attrs)) if (v !== null && v !== undefined) node.setAttribute(k, v);
    for (const c of children.flat()) if (c) node.append(c.nodeType ? c : document.createTextNode(String(c)));
    return node;
  };
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const usd = (v) => (v === null || v === undefined ? "—" : v === 0 ? "$0.00" : v >= 0.1 ? `$${v.toFixed(2)}` : v >= 0.01 ? `$${v.toFixed(3)}` : `$${v.toFixed(5)}`);
  const pct = (v) => (v === null || v === undefined ? "—" : `${Math.round(v * 100)}%`);
  const title = (s) => String(s ?? "").replace(/_/g, " ");
  const TIERS = ["hot", "warm", "nurture", "disqualify", "existing"];
  const TIER_LABEL = { hot: "Hot", warm: "Warm", nurture: "Nurture", disqualify: "Disqualified", existing: "Existing account" };
  const TIER_SUB = { hot: "founder call · two slots offered", warm: "SDR sequence A", nurture: "newsletter · content track", disqualify: "polite decline drafted, never sent", existing: "handed to the account owner" };
  const toast = (msg, err = false) => {
    const t = $("#toast");
    t.textContent = msg; t.className = "toast" + (err ? " err" : ""); t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), err ? 6000 : 3200);
  };
  const api = async (url, opts = {}) => {
    const r = await fetch(url, { headers: { "Content-Type": "application/json" }, ...opts });
    if (!r.ok) { let msg = r.statusText; try { const j = await r.json(); msg = (j.detail && j.detail.refusal) || j.detail || msg; } catch (_) {} throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg)); }
    return r.json();
  };
  const busy = (btn, on) => { if (!btn) return; btn.classList.toggle("busy", on); btn.disabled = on; };
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

  const state = { status: null, leads: [], leadsById: {}, results: {}, totals: null, metrics: null, icp: null, icpDraft: null, presets: [], playbook: null,
                  currentLead: null, running: false, lastRun: null, evidenceOff: new Set(), filters: {}, mode: "viewing" };
  const session = { cost: 0, requests: 0, latencies: [] };

  // ------------------------------------------------------------------ theme
  const setTheme = (t) => { document.documentElement.setAttribute("data-theme", t); try { localStorage.setItem("fr-theme", t); } catch (_) {} };
  $("#btn-theme").addEventListener("click", () => setTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark"));

  // ------------------------------------------------------------------ nav
  const showPage = (name) => {
    $$(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.page === name));
    $$(".page").forEach((p) => p.classList.toggle("active", p.id === `page-${name}`));
    if (name === "icp") loadICP();
    if (name === "explore") renderExplore();
    if (name === "accuracy") renderAccuracy();
    if (name === "connect") renderConnect();
    if (name === "review") { state.mode = "reviewing"; loadReview(); } else state.mode = "viewing";
    if (name === "lead" && !state.currentLead && state.leads.length) openLead(state.leads[0].id);
    if (name === "lead" && state.currentLead) history.replaceState(null, "", `#lead/${state.currentLead}`);
    else history.replaceState(null, "", `#${name}`);
  };
  $$(".nav-btn").forEach((b) => b.addEventListener("click", () => showPage(b.dataset.page)));

  // ------------------------------------------------------------------ status + data
  async function loadStatus() {
    try {
      const s = await api("/api/status");
      state.status = s;
      $("#client-name").textContent = s.icp.client; $("#icp-name").textContent = s.icp.name; $("#lead-count").textContent = s.leads; $("#model-name").textContent = s.model;
      $("#k-done-ctx").textContent = `of ${s.leads}`;
      const pill = $("#status-pill");
      pill.className = "pill " + (s.jev_key ? "good" : "bad");
      pill.innerHTML = `<span class="dot-status"></span>${s.fake ? "fake Jev (offline)" : s.jev_key ? "Jev ready" : "no Jev key"}`;
      $("#key-banner").hidden = !!s.jev_key;
    } catch (e) {
      $("#status-pill").className = "pill bad"; $("#status-pill").innerHTML = `<span class="dot-status"></span>offline`;
    }
  }
  async function loadLeads() {
    state.leads = await api("/api/leads");
    state.leadsById = Object.fromEntries(state.leads.map((l) => [l.id, l]));
    const sel = $("#lead-select"); sel.innerHTML = "";
    for (const l of state.leads) sel.append(el("option", { value: l.id }, `${l.id} · ${l.company_name} — ${l.person_name}`));
  }
  async function loadResults() {
    const r = await api("/api/results");
    state.results = Object.fromEntries(r.results.map((x) => [x.lead_id, x]));
    state.totals = r.totals; state.metrics = r.metrics; state.stale = r.stale;
    renderAll();
    return r;
  }
  function renderAll() {
    renderKpis(); renderValue(); renderBoard();
    if ($("#page-explore").classList.contains("active")) renderExplore();
    if ($("#page-accuracy").classList.contains("active")) renderAccuracy();
  }

  // ------------------------------------------------------------------ run (SSE)
  const MISSING_KEY = "Add your TypeSafe key to run this live: put TYPESAFE_API_KEY=… in .env (copy .env.example) and restart ./run.sh serve.";
  async function run(force = false, ids = null) {
    if (state.running) return null;
    if (state.status && !state.status.jev_key) { toast(MISSING_KEY, true); return null; }
    state.running = true;
    const btns = [$("#btn-run"), $("#btn-run-2"), $("#btn-run-fresh")]; btns.forEach((b) => busy(b, true));
    showPage("pipeline");
    const total = ids ? ids.length : state.leads.length;
    if (!ids) { state.results = {}; renderBoard(true); }
    const bar = $("#runbar"); bar.className = "runbar"; bar.firstElementChild.style.width = "2%";
    $("#board-title").innerHTML = `Streaming — <b>0</b> / ${total}`;
    const t0 = performance.now();
    let done = 0, doneEvent = null, tokens = 0, cost = 0, asked = 0, lats = [];
    try {
      const r = await fetch(`/api/run/stream?force=${force ? 1 : 0}${ids ? `&ids=${ids.join(",")}` : ""}`);
      if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
      const reader = r.body.getReader(); const dec = new TextDecoder(); let buf = "";
      while (true) {
        const { value, done: fin } = await reader.read();
        if (fin) break;
        buf += dec.decode(value, { stream: true });
        let idx;
        while ((idx = buf.indexOf("\n\n")) >= 0) {
          const chunk = buf.slice(0, idx); buf = buf.slice(idx + 2);
          let kind = "message", data = null;
          for (const line of chunk.split("\n")) { if (line.startsWith("event:")) kind = line.slice(6).trim(); else if (line.startsWith("data:")) data = JSON.parse(line.slice(5)); }
          if (!data) continue;
          if (kind === "result") {
            done++; state.results[data.lead_id] = data;
            if (data.meta.n_asked) { asked++; tokens += data.meta.input_tokens; cost += data.meta.cost_usd; lats.push(data.meta.latency_ms); }
            addCard(data); updateRunKpis(done, total, asked, tokens, cost, lats, performance.now() - t0);
          } else if (kind === "failed") { done++; toast(`${data.lead_id}: ${data.message}`, true); }
          else if (kind === "done") { doneEvent = data; }
          else if (kind === "fatal") { toast(data.message, true); }
        }
      }
    } catch (e) { toast(e.message, true); }
    state.running = false; btns.forEach((b) => busy(b, false));
    bar.className = "runbar done"; bar.firstElementChild.style.width = "100%";
    if (doneEvent) {
      const t = doneEvent.totals; state.lastRun = doneEvent;
      session.cost += t.cost_usd; session.requests += t.requests; session.latencies.push(...lats);
      $("#run-meta").textContent = `${t.leads} leads · ${t.requests} requests · ${t.elapsed_s}s · ${usd(t.cost_usd)} · ${t.from_cache} from cache`;
      if (doneEvent.metrics) state.metrics = doneEvent.metrics;
    }
    await loadResults();
    return doneEvent;
  }
  $("#btn-run").addEventListener("click", () => run(false));
  $("#btn-run-2").addEventListener("click", () => run(false));
  $("#btn-run-fresh").addEventListener("click", () => run(true));

  function updateRunKpis(done, total, asked, tokens, cost, lats, wall) {
    $("#runbar").firstElementChild.style.width = `${Math.max(2, (done / total) * 100)}%`;
    $("#board-title").innerHTML = `Streaming — <b>${done}</b> / ${total} · ${(wall / 1000).toFixed(1)} s`;
    $("#k-done").textContent = done;
    $("#k-req").textContent = asked; $("#k-req-ctx").textContent = asked ? `${(tokens / asked).toFixed(0)} tokens each · ${done - asked} from cache` : `${done} from cache`;
    const mean = lats.length ? lats.reduce((a, b) => a + b, 0) / lats.length : null;
    $("#k-lat").textContent = mean ? `${Math.round(mean)} ms` : "—"; $("#k-lat-ctx").textContent = mean ? `mean per request · ${(wall / 1000).toFixed(1)} s wall` : "served from cache";
    $("#k-cost").textContent = usd(cost); $("#k-cost-ctx").textContent = `${tokens.toLocaleString()} input tokens`;
    $("#k-proj").textContent = asked ? `$${((cost / asked) * 1000).toFixed(2)}` : "—";
    const review = Object.values(state.results).filter((r) => r.confidence.needs_review).length;
    $("#k-review").textContent = review; $("#k-review-ctx").textContent = `${done ? Math.round(((done - review) / done) * 100) : 0}% routed without a human`;
  }
  function renderKpis() {
    const rs = Object.values(state.results); const n = rs.length;
    if (!n) { ["k-done", "k-req", "k-lat", "k-cost", "k-proj", "k-review"].forEach((id) => ($(`#${id}`).textContent = "—")); return; }
    const t = state.totals || {};
    const hist = state.status?.cache || {};
    $("#k-done").textContent = n;
    const asked = state.lastRun?.totals?.requests ?? 0;
    $("#k-req").textContent = asked; $("#k-req-ctx").textContent = asked ? `${t.questions_per_lead} questions each` : `all ${n} served from cache · ${t.questions_per_lead} questions each`;
    const lat = state.lastRun?.totals?.latency_mean_ms ?? hist.latency_mean_ms;
    $("#k-lat").textContent = lat ? `${Math.round(lat)} ms` : "—"; $("#k-lat-ctx").textContent = asked ? `mean per request · ${state.lastRun.totals.elapsed_s} s for ${n} leads` : "mean of past requests";
    $("#k-cost").textContent = usd(state.lastRun?.totals?.cost_usd ?? 0); $("#k-cost-ctx").textContent = asked ? `${state.lastRun.totals.input_tokens.toLocaleString()} input tokens` : "0 tokens — served from cache";
    const per1k = state.lastRun?.totals?.cost_per_1000_usd ?? (hist.requests ? (hist.tokens_in / hist.requests) * 1000 * (state.status.price_per_m / 1e6) : null);
    $("#k-proj").textContent = per1k !== null && per1k !== undefined ? `$${per1k.toFixed(2)}` : "—";
    $("#k-review").textContent = t.needs_review; $("#k-review-ctx").textContent = `${Math.round((t.auto_routed / n) * 100)}% routed without a human`;
    $("#board-title").innerHTML = `${n} leads · ${TIERS.map((k) => `<b>${t.tiers[k]}</b> ${TIER_LABEL[k].toLowerCase()}`).join(" · ")}`;
  }
  function renderValue() {
    const rs = Object.values(state.results); const n = rs.length; const t = state.totals || { tiers: {}, auto_routed: 0 };
    const hist = state.status?.cache || {};
    const per1k = state.lastRun?.totals?.cost_per_1000_usd ?? (hist.requests ? (hist.tokens_in / hist.requests) * 1000 * (state.status.price_per_m / 1e6) : null);
    const lats = session.latencies.length ? [...session.latencies].sort((a, b) => a - b) : null;
    $("#v-leads").textContent = n;
    const mins = n * (state.status?.sdr_minutes_per_lead || 6);
    $("#v-minutes").textContent = mins >= 60 ? `${(mins / 60).toFixed(1)} h` : `${mins} min`;
    $("#v-auto").textContent = n ? pct(t.auto_routed / n) : "—";
    $("#v-cost1k").textContent = per1k !== null && per1k !== undefined ? `$${per1k.toFixed(2)}` : "—";
    $("#v-lat").textContent = lats ? `${lats[Math.floor(lats.length / 2)]} ms` : hist.latency_mean_ms ? `${Math.round(hist.latency_mean_ms)} ms` : "—";
    $("#v-cost").textContent = usd(session.cost);
    $("#v-protected").textContent = t.tiers.disqualify ?? 0; $("#v-dupes").textContent = t.tiers.existing ?? 0;
    $("#value-summary").textContent = n ? `— ${n} leads · ${mins >= 60 ? (mins / 60).toFixed(1) + " h" : mins + " min"} saved · ${pct(t.auto_routed / n)} auto-routed` : "";
  }
  $("#value-toggle").addEventListener("click", () => { const t = $("#value-toggle"); t.setAttribute("aria-expanded", t.getAttribute("aria-expanded") === "true" ? "false" : "true"); });

  // ------------------------------------------------------------------ tier board
  const painIndex = (pid) => { const pains = Object.keys(state.icp?.pains || {}); const i = pains.indexOf(pid); return i < 0 ? 6 : (i % 6) + 1; };
  const painStyle = (pid) => `--pc: var(--p${painIndex(pid)}); --pci: var(--p${painIndex(pid)}-ink)`;
  function renderBoard(skeleton = false) {
    const board = $("#board"); board.innerHTML = "";
    for (const tier of TIERS) {
      const col = el("div", { class: "col", "data-tier": tier, id: `col-${tier}` });
      col.append(el("div", { class: "col-title" }, el("h4", {}, TIER_LABEL[tier]), el("span", { class: "n", id: `n-${tier}` }, "0")), el("div", { class: "col-sub" }, TIER_SUB[tier]));
      if (skeleton) for (let i = 0; i < 3; i++) col.append(el("div", { class: "skel" }));
      else col.append(el("div", { class: "placeholder" }, "—"));
      board.append(col);
    }
    if (!skeleton) {
      const rs = Object.values(state.results).sort((a, b) => (b.fit + b.intent) - (a.fit + a.intent));
      rs.forEach((r, i) => addCard(r, i));
    }
  }
  function addCard(r, i = 0) {
    const col = $(`#col-${r.tier}`); if (!col) return;
    col.querySelectorAll(".placeholder, .skel").forEach((x) => x.remove());
    const old = $(`#lc-${r.lead_id}`); if (old) old.remove();
    const lead = state.leadsById[r.lead_id] || {};
    const c = el("div", { class: `lcard${r.confidence.needs_review ? " review" : ""}`, id: `lc-${r.lead_id}`, style: `--i:${i}`, onclick: () => openLead(r.lead_id) });
    c.append(el("div", { class: "top" }, el("div", { style: "min-width:0" }, el("div", { class: "co" }, lead.company_name || r.lead_id), el("div", { class: "who" }, `${lead.person_name || ""}${lead.person?.title ? " · " + lead.person.title : ""}`)),
      el("span", { class: `conf ${r.confidence.label}`, title: r.confidence.reasons.join("\n") || "confident" }, r.confidence.label === "low" ? "human" : r.confidence.min_confidence.toFixed(2))));
    const chips = el("div", { class: "chips" });
    if (r.components.persona.choice && r.components.persona.choice !== "other") chips.append(el("span", { class: "chip persona" }, title(r.components.persona.choice)));
    if (r.primary_pain) chips.append(el("span", { class: "chip pain", style: painStyle(r.primary_pain) }, title(r.primary_pain)));
    if (r.tier === "disqualify" && r.disqualifiers.length) chips.append(el("span", { class: "chip" }, r.disqualifiers[0].label));
    if (r.tier === "existing" && r.existing_account) chips.append(el("span", { class: "chip" }, `${r.existing_account.status} · ${r.existing_account.owner}`));
    chips.append(el("span", { class: "chip src" }, lead.source_label || lead.source || ""));
    c.append(chips);
    c.append(el("div", { class: "bars" },
      el("div", { class: "bar" }, el("span", {}, "fit ", el("b", {}, r.fit.toFixed(2))), el("div", { class: "tr" }, el("i", { style: `width:${r.fit * 100}%` }))),
      el("div", { class: "bar intent" }, el("span", {}, "intent ", el("b", {}, r.intent.toFixed(2))), el("div", { class: "tr" }, el("i", { style: `width:${r.intent * 100}%` })))));
    c.append(el("div", { class: "foot" }, el("span", { class: "act", title: r.next_action.text }, r.next_action.label), r.meta?.cached ? el("span", { class: "chip src", title: "answers served from cache" }, "cache") : null));
    // keep the column sorted by fit+intent
    const cards = Array.from(col.querySelectorAll(".lcard"));
    const score = r.fit + r.intent;
    const before = cards.find((x) => { const rr = state.results[x.id.slice(3)]; return rr && rr.fit + rr.intent < score; });
    if (before) col.insertBefore(c, before); else col.append(c);
    for (const t of TIERS) { $(`#n-${t}`).textContent = $(`#col-${t}`).querySelectorAll(".lcard").length; capColumn($(`#col-${t}`)); }
  }
  const CAP = 8;
  function capColumn(col) {
    if (col.dataset.expanded === "1") return;
    const cards = Array.from(col.querySelectorAll(".lcard"));
    cards.forEach((c, i) => (c.hidden = i >= CAP));
    let more = col.querySelector(".more");
    if (cards.length > CAP) {
      if (!more) { more = el("button", { class: "btn small ghost more", onclick: () => { col.dataset.expanded = "1"; cards.forEach((c) => (c.hidden = false)); col.querySelectorAll(".lcard").forEach((c) => (c.hidden = false)); more.remove(); } }); col.append(more); }
      more.textContent = `Show all ${cards.length}`; col.append(more);
    } else if (more) more.remove();
  }

  // ------------------------------------------------------------------ lead page
  async function openLead(id, flash = false) {
    state.currentLead = id;
    $("#lead-select").value = id;
    showPageQuiet("lead");
    history.replaceState(null, "", `#lead/${id}`);
    const d = await api(`/api/leads/${id}`);
    renderLead(d);
    if (flash) { $("#tier-card").classList.remove("flash"); void $("#tier-card").offsetWidth; $("#tier-card").classList.add("flash"); }
    return d;
  }
  function showPageQuiet(name) { $$(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.page === name)); $$(".page").forEach((p) => p.classList.toggle("active", p.id === `page-${name}`)); history.replaceState(null, "", `#${name}`); }
  $("#lead-select").addEventListener("change", (e) => openLead(e.target.value));
  $("#btn-score-one").addEventListener("click", async () => {
    if (!state.currentLead) return;
    const btn = $("#btn-score-one"); busy(btn, true);
    try {
      const r = await api(`/api/score/${state.currentLead}?force=1`, { method: "POST" });
      state.results[r.lead_id] = r; session.cost += r.meta.cost_usd; session.latencies.push(r.meta.latency_ms);
      $("#lead-meta").textContent = `1 request · ${r.meta.n_asked} questions · ${r.meta.latency_ms} ms · ${r.meta.input_tokens.toLocaleString()} tokens · ${usd(r.meta.cost_usd)} · ${r.meta.model}`;
      await openLead(state.currentLead, true); await loadResults();
    } catch (e) { toast(e.message, true); }
    busy(btn, false);
  });

  function renderLead(d) {
    const { lead, result: r } = d;
    $("#lead-title").textContent = `${lead.company_name} — ${lead.person_name}`;
    $("#lead-sub").textContent = `${lead.source_label} · received ${lead.received_at.slice(0, 10)} · ${lead.shape === "message" ? "inbound message" : lead.shape === "bio" ? "executive bio" : "company profile"}${lead.tags?.length ? " · " + lead.tags.join(", ") : ""}`;
    const contact = lead.contact?.kind === "revealed" ? lead.contact.address : "hidden";
    if ($("#lead-disp")) $("#lead-disp").textContent = `${lead.disposition || "unreviewed"} · contact ${contact}`;
    if (!r) {
      $("#lead-empty").hidden = false; $("#lead-grid").hidden = true;
      $("#lead-empty").innerHTML = `<div class="empty-mark">¶</div><p>${esc(lead.company_name)} has not been scored yet. Press <b>Score this lead now</b> (one Jev request) or run the whole pipeline.</p>`;
      $("#lead-meta").textContent = ""; return;
    }
    $("#lead-empty").hidden = true; $("#lead-grid").hidden = false;
    if (!$("#lead-meta").textContent || !$("#lead-meta").textContent.startsWith("1 request")) $("#lead-meta").textContent = r.meta?.cached ? `served from cache · ${r.meta.n_questions} questions` : `${r.meta.n_asked} questions asked · ${r.meta.latency_ms} ms`;
    renderTierCard(lead, r); renderMessage(lead, r); renderCompany(lead, r); renderPerson(lead, r);
    renderQuadrant(r); renderChecklist(r); renderDedupe(r); renderAction(r); renderAnswers(d);
  }
  function renderTierCard(lead, r) {
    const c = $("#tier-card"); c.setAttribute("data-tier", r.tier); c.innerHTML = "";
    const conf = r.confidence;
    c.append(el("div", { class: "tier-row" }, el("span", { class: "tier-big" }, TIER_LABEL[r.tier]),
      el("span", { class: `conf ${conf.label}` }, conf.label === "low" ? "needs a human" : `confidence ${conf.label} · ${conf.min_confidence.toFixed(2)}`),
      el("div", { class: "tier-scores" }, el("div", { class: "s" }, el("div", { class: "k" }, "ICP fit"), el("div", { class: "v" }, r.fit.toFixed(2))), el("div", { class: "s" }, el("div", { class: "k" }, "Intent"), el("div", { class: "v" }, r.intent.toFixed(2))))));
    const route = r.route;
    const box = el("div", { class: "route-box" },
      el("div", {}, el("div", { class: "k" }, "Route"), el("div", { class: "v" }, route.label)),
      el("div", {}, el("div", { class: "k" }, "Owner"), el("div", { class: "v" }, route.owner || "—")),
      el("div", { style: "grid-column:1/-1" }, el("div", { class: "k" }, "Action"), el("div", { class: "v muted" }, route.action || "—")));
    if (route.slots) box.append(el("div", { style: "grid-column:1/-1" }, el("div", { class: "k" }, "Call slots proposed"), el("div", { class: "slots" }, ...route.slots.map((s) => el("span", { class: "slot" }, s)))));
    c.append(box);
    c.append(el("div", { class: "why", html: `<b>Why:</b> ${r.why.map(esc).join(" · ")}` }));
    if (route.hold) c.append(el("div", { class: "hold", html: `<b>On hold —</b> ${esc(route.hold_reason)}${conf.reasons.length > 1 ? "<br>" + conf.reasons.slice(1).map(esc).join("<br>") : ""}` }));
    if (r.flags.length) c.append(el("div", { class: "flags" }, ...r.flags.map((f) => el("div", { class: `flag ${f.severity}` }, el("span", { class: "ic" }, f.severity === "warn" ? "!" : "i"), el("span", {}, f.text)))));
  }
  function sentenceSpan(s, r) {
    const cls = ["sent"]; let style = ""; let tip = [];
    for (const [pid, ev] of Object.entries(r.evidence.pains)) if (ev.sentence === s.id && !state.evidenceOff.has(pid)) { cls.push("pain"); style = painStyle(pid); tip.push(`${title(pid)} · P ${ev.p.toFixed(2)}`); }
    if (r.evidence.intent?.sentence === s.id) { cls.push("intent"); tip.push(`buying intent · P ${r.evidence.intent.p.toFixed(2)}`); }
    return el("span", { class: cls.join(" "), style, title: tip.join("\n") || null, "data-sid": s.id }, el("span", { class: "sid" }, s.id), s.text, " ");
  }
  function evidenceLegend(r) {
    const lg = el("div", { class: "evlegend" }, el("span", {}, "Evidence:"));
    const pains = Object.entries(r.components.pains.scores).sort((a, b) => b[1] - a[1]);
    for (const [pid, p] of pains) {
      if (p < 0.2 && !r.evidence.pains[pid]) continue;
      lg.append(el("span", { class: `chip pain${state.evidenceOff.has(pid) ? " off" : ""}`, style: painStyle(pid), onclick: () => { state.evidenceOff.has(pid) ? state.evidenceOff.delete(pid) : state.evidenceOff.add(pid); renderLead({ lead: state.leadsById[r.lead_id], result: r, questions: state.lastQuestions }); } }, `${title(pid)} ${p.toFixed(2)}`));
    }
    lg.append(el("span", {}, el("i", { class: "il" }), "buying intent"));
    return lg;
  }
  function renderMessage(lead, r) {
    const c = $("#message-card"); c.innerHTML = "";
    if (!lead.message?.text) { c.append(el("div", { class: "card-head" }, el("div", {}, el("div", { class: "eyebrow" }, "Message"), el("h3", {}, "No message"))), el("p", { class: "small muted" }, "This lead arrived as a profile or bio export. Intent comes from news and bio; the lead is scored on fit.")); return; }
    c.append(el("div", { class: "card-head" }, el("div", {}, el("div", { class: "eyebrow" }, `Message · ${lead.source_label}`), el("h3", {}, lead.message.subject || `From ${lead.person_name}`)),
      el("div", { class: "legend" }, lead.message.from_domain ? el("span", { class: "pill" }, lead.message.from_domain) : null, el("span", { class: "pill accent" }, `${lead.sentences.filter((s) => s.part === "message").length} sentences`))));
    const msg = el("div", { class: "msg" });
    for (const s of lead.sentences.filter((s) => s.part === "message")) msg.append(sentenceSpan(s, r));
    c.append(msg, evidenceLegend(r));
  }
  function renderCompany(lead, r) {
    const c = $("#company-card"); c.innerHTML = "";
    const co = lead.company;
    c.append(el("div", { class: "card-head" }, el("div", {}, el("div", { class: "eyebrow" }, "Company profile"), el("h3", {}, co?.name || "Unknown company")),
      el("div", { class: "legend" }, co?.domain ? el("span", { class: "pill mono" }, co.domain) : null, el("span", { class: "pill accent" }, title(r.components.industry.choice || "—")))));
    if (!co) { c.append(el("p", { class: "small muted" }, "No company profile attached — industry and maturity are inferred from the message and bio.")); return; }
    const kv = el("div", { class: "kv-grid" });
    kv.append(kvNode("Description", co.description, "plain"), kvNode("Location", co.location), kvNode("Stated size", co.size || "not stated"), kvNode("Services", (co.services || []).join(" · ") || "—", "plain"));
    c.append(kv);
    if (co.news) {
      c.append(el("div", { class: "kv", style: "margin-top:10px" }, el("div", { class: "k" }, "Recent news")));
      const m = el("div", { class: "msg", style: "margin-top:4px" }); for (const s of lead.sentences.filter((s) => s.part === "news")) m.append(sentenceSpan(s, r)); c.append(m);
    }
    const mat = r.components.maturity;
    c.append(el("div", { class: "kv-grid", style: "margin-top:10px" }, kvNode("Maturity (Jev)", mat.level === null ? "—" : `level ${mat.level} / 4 · fit ${mat.fit.toFixed(2)} · conf ${mat.confidence.toFixed(2)}`), kvNode("Industry fit", `${r.components.industry.fit.toFixed(2)} · conf ${r.components.industry.confidence.toFixed(2)}`)));
  }
  function renderPerson(lead, r) {
    const c = $("#person-card"); c.innerHTML = "";
    const p = lead.person; const per = r.components.persona;
    c.append(el("div", { class: "card-head" }, el("div", {}, el("div", { class: "eyebrow" }, "Person"), el("h3", {}, p?.name || lead.person_name)),
      el("div", { class: "legend" }, el("span", { class: "chip persona" }, title(per.choice || "—")), el("span", { class: "pill" }, `authority ${per.authority.toFixed(1)} / 3`))));
    if (!p) { c.append(el("p", { class: "small muted" }, "No person attached.")); return; }
    c.append(el("div", { class: "kv-grid" }, kvNode("Title", p.title || "—"), kvNode("Location", p.location || "—"), kvNode("Persona fit", `${per.fit.toFixed(2)} · conf ${per.confidence.toFixed(2)}`)));
    if (p.bio) {
      c.append(el("div", { class: "kv", style: "margin-top:10px" }, el("div", { class: "k" }, "Bio")));
      const m = el("div", { class: "msg", style: "margin-top:4px" }); for (const s of lead.sentences.filter((s) => s.part === "bio")) m.append(sentenceSpan(s, r)); c.append(m);
    }
    c.append(el("p", { class: "small muted", style: "margin-top:10px" }, "E-mail addresses and phone numbers are never sent to Jev."));
  }
  const kvNode = (k, v, cls = "") => el("div", { class: "kv" }, el("div", { class: "k" }, k), el("div", { class: "v " + cls }, String(v ?? "—")));

  function renderQuadrant(r) {
    const c = $("#quadrant-card"); c.innerHTML = "";
    const t = state.icp?.thresholds || { fit_hot: .62, fit_warm: .42, intent_hot: .6, intent_warm: .25 };
    c.append(el("div", { class: "card-head" }, el("div", {}, el("div", { class: "eyebrow" }, "Fit × intent"), el("h3", {}, "Where it sits, and why"))));
    const W = 220, H = 220, pad = 22;
    const svg = svgel("svg", { viewBox: `0 0 ${W} ${H}`, class: "quad" });
    const x = (v) => pad + v * (W - pad - 6), y = (v) => H - pad - v * (H - pad - 6);
    const M = { hot: "var(--hot)", warm: "var(--warm)", nurture: "var(--nurture)" };
    const MATRIX = { "high,high": "hot", "high,mid": "warm", "high,low": "nurture", "mid,high": "warm", "mid,mid": "warm", "mid,low": "nurture", "low,high": "warm", "low,mid": "nurture", "low,low": "nurture" };
    const fb = [[0, t.fit_warm, "low"], [t.fit_warm, t.fit_hot, "mid"], [t.fit_hot, 1, "high"]], ib = [[0, t.intent_warm, "low"], [t.intent_warm, t.intent_hot, "mid"], [t.intent_hot, 1, "high"]];
    for (const [f0, f1, fbnd] of fb) for (const [i0, i1, ibnd] of ib) svg.append(svgel("rect", { class: "zone", x: x(f0), y: y(i1), width: x(f1) - x(f0), height: y(i0) - y(i1), fill: M[MATRIX[`${fbnd},${ibnd}`]], opacity: .13 }));
    for (const v of [t.fit_warm, t.fit_hot]) svg.append(svgel("line", { class: "thr", x1: x(v), x2: x(v), y1: y(0), y2: y(1) }));
    for (const v of [t.intent_warm, t.intent_hot]) svg.append(svgel("line", { class: "thr", x1: x(0), x2: x(1), y1: y(v), y2: y(v) }));
    svg.append(svgel("text", { class: "lbl", x: x(0.5), y: H - 5, "text-anchor": "middle" }, "ICP fit →"), svgel("text", { class: "lbl", x: 8, y: y(0.5), transform: `rotate(-90 8 ${y(0.5)})`, "text-anchor": "middle" }, "intent →"));
    svg.append(svgel("text", { class: "lbl", x: x(1) - 3, y: y(1) + 10, "text-anchor": "end", fill: "var(--hot)" }, "hot"), svgel("text", { class: "lbl", x: x(1) - 3, y: y(0) - 4, "text-anchor": "end", fill: "var(--nurture)" }, "nurture"));
    svg.append(svgel("circle", { class: "pt", cx: x(r.fit), cy: y(r.intent), r: 6 }));
    const contrib = el("div", { class: "contrib" });
    contrib.append(el("div", { class: "h" }, `Fit ${r.fit.toFixed(2)} = weighted components`));
    const w = state.icp?.weights || {};
    for (const [k, v] of Object.entries(r.fit_contrib)) contrib.append(el("div", { class: "row" }, el("span", {}, `${k} ×${w[k] ?? ""}`), el("div", { class: "tr" }, el("i", { style: `width:${Math.min(100, v * 100 / Math.max(0.01, (w[k] || 0.25) / Object.values(w).reduce((a, b) => a + b, 0)))}%` })), el("span", { class: "n" }, `+${v.toFixed(2)}`)));
    contrib.append(el("div", { class: "h" }, `Intent ${r.intent.toFixed(2)} = weighted signals`));
    const iw = state.icp?.intent_weights || {};
    for (const [k, v] of Object.entries(r.intent_contrib)) contrib.append(el("div", { class: "row intent" }, el("span", {}, `${title(k)} ×${iw[k] ?? ""}`), el("div", { class: "tr" }, el("i", { style: `width:${Math.min(100, v * 100 / Math.max(0.01, (iw[k] || 0.2) / Object.values(iw).reduce((a, b) => a + b, 0)))}%` })), el("span", { class: "n" }, `+${v.toFixed(2)}`)));
    c.append(el("div", { class: "quad" }, svg, contrib));
    c.append(el("div", { class: "moveup" }, el("div", { class: "k" }, "What would move it up a tier"), el("div", {}, r.move_up)));
  }
  function renderChecklist(r) {
    const c = $("#checklist-card"); c.innerHTML = "";
    c.append(el("div", { class: "card-head" }, el("div", {}, el("div", { class: "eyebrow" }, "ICP checklist"), el("h3", {}, "Literal answers, never guessed"))));
    c.append(el("div", { class: "checks" }, ...r.checklist.map((i) => el("div", { class: `check ${i.state}` }, el("span", { class: "ck" }, i.state === "ok" ? "✓" : i.state === "fail" ? "✗" : i.state === "warn" ? "!" : "?"), el("span", {}, i.label), el("span", { class: "d" }, i.detail)))));
    const pains = el("div", { class: "pains" });
    pains.append(el("div", { class: "h", style: "font-size:.66rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:600;margin-top:8px" }, "Qualifying pains · one yes/no each"));
    for (const [pid, p] of Object.entries(r.components.pains.scores).sort((a, b) => b[1] - a[1])) pains.append(el("div", { class: `row${pid === r.primary_pain ? " primary" : ""}`, style: painStyle(pid) }, el("span", { class: "name" }, title(pid)), el("div", { class: "tr" }, el("i", { style: `width:${p * 100}%` })), el("span", { class: "n" }, p.toFixed(2))));
    c.append(pains);
  }
  function renderDedupe(r) {
    const c = $("#dedupe-card"); c.innerHTML = "";
    const d = r.dedupe;
    c.append(el("div", { class: "card-head" }, el("div", {}, el("div", { class: "eyebrow" }, "CRM dedupe · entity alignment"), el("h3", {}, r.existing_account ? `Same organisation as ${r.existing_account.name}` : d.candidates.length ? "Shortlisted, not the same" : "No similar account in the CRM")),
      el("span", { class: `pill ${r.existing_account ? "good" : ""}` }, d.candidates.length ? `${d.candidates.length} candidate${d.candidates.length > 1 ? "s" : ""} · Jev decides` : "code found nothing")));
    if (!d.candidates.length) { c.append(el("p", { class: "small muted" }, "Code compares domain and name against every CRM account; nothing came close, so Jev was not asked.")); return; }
    const probs = r.answers.same_account?.probabilities || {};
    const list = el("div", { class: "cands" });
    for (const cand of d.candidates) list.append(el("div", { class: `cand${r.existing_account?.id === cand.id ? " match" : ""}` }, el("span", { class: "nm" }, `${cand.name} · ${cand.status}`), el("span", { class: "p" }, `P(same) ${(probs[cand.id] ?? 0).toFixed(2)}`), el("span", { class: "dm" }, `${cand.domain} · owner ${cand.owner}`), el("span", { class: "rs" }, `code: ${cand.code_reasons.join(", ")} (${cand.code_score})`)));
    list.append(el("div", { class: `cand${!r.existing_account ? " match" : ""}` }, el("span", { class: "nm" }, "none — a different company"), el("span", { class: "p" }, `P ${(probs.none ?? 0).toFixed(2)}`)));
    c.append(list);
  }
  function renderAction(r) {
    const c = $("#action-card"); c.innerHTML = "";
    const a = r.next_action;
    c.append(el("div", { class: "card-head" }, el("div", {}, el("div", { class: "eyebrow" }, "Next best action · playbook"), el("h3", {}, a.label)), el("span", { class: "pill accent" }, a.source === "rule" ? "fixed by tier" : a.source === "jev" ? `Jev · ${a.jev_confidence.toFixed(2)}` : "Jev, constrained to tier")));
    c.append(el("div", { class: "playbook" }, el("div", { class: "h" }, el("b", {}, a.label), el("span", { class: "muted small" }, r.tier === "disqualify" ? "draft — never auto-sent" : r.tier === "existing" ? "internal note" : "template filled in code")), el("div", {}, a.text)));
    if (a.jev_choice && a.jev_choice !== a.id) c.append(el("p", { class: "small muted", style: "margin-top:8px" }, `Jev's unconstrained pick was “${title(a.jev_choice)}”; the tier's allowed actions override it.`));
    if (r.timeline.choice && r.timeline.choice !== "not_stated") c.append(el("p", { class: "small", style: "margin-top:8px" }, `Timeline stated: ${title(r.timeline.choice)} (${r.timeline.confidence.toFixed(2)})`));
  }
  function renderAnswers(d) {
    const { result: r, questions } = d; state.lastQuestions = questions;
    const c = $("#answers-card"); c.innerHTML = "";
    const head = el("button", { class: "card-head toggle", "aria-expanded": "false", onclick: (e) => { const b = e.currentTarget; b.setAttribute("aria-expanded", b.getAttribute("aria-expanded") === "true" ? "false" : "true"); } },
      el("div", {}, el("div", { class: "eyebrow" }, "All answers"), el("h3", {}, `${Object.keys(r.answers).length} questions, one request `, el("span", { class: "muted-h" }, r.questions_asked?.length ? `— ${r.questions_asked.length} asked fresh, rest from cache` : "— all from cache"))), el("span", { class: "chev" }, "▾"));
    c.append(head);
    const table = el("table", { class: "answers" }, el("thead", {}, el("tr", {}, el("th", {}, "Question"), el("th", {}, "Group"), el("th", {}, "Answer"), el("th", {}, "Probability / confidence"))));
    const tb = el("tbody");
    const fresh = new Set(r.questions_asked || []);
    for (const q of questions) {
      const a = r.answers[q.id]; if (!a) continue;
      let ans = "", pr = "";
      if (a.type === "noul") { ans = a.p >= 0.5 ? "yes" : "no"; pr = `<span class="pbar"><i style="width:${a.p * 100}%"></i></span>${a.p.toFixed(2)}`; }
      else if (a.type === "choice") { ans = title(a.choice); pr = `<span class="pbar"><i style="width:${(a.probabilities[a.choice] || 0) * 100}%"></i></span>P ${(a.probabilities[a.choice] || 0).toFixed(2)} · conf ${a.confidence.toFixed(2)}`; }
      else { ans = `level ${a.level} of ${a.n_levels - 1} (score ${a.score.toFixed(2)})`; pr = `<span class="pbar"><i style="width:${(a.score / (a.n_levels - 1)) * 100}%"></i></span>conf ${a.confidence.toFixed(2)}`; }
      tb.append(el("tr", { class: fresh.has(q.id) ? "fresh" : "" }, el("td", { class: "id", title: q.text }, q.id), el("td", { class: "grp" }, q.group), el("td", {}, ans), el("td", { html: pr })));
    }
    table.append(tb); c.append(table);
  }

  // ------------------------------------------------------------------ ICP editor
  const clone = (o) => JSON.parse(JSON.stringify(o));
  async function loadICP(force = false) {
    if (state.icp && !force && $("#preset-select").options.length) { if (!state.icpDraft) { state.icpDraft = clone(state.icp); renderICPForm(); } refreshLive(); return; }
    const d = await api("/api/icp");
    state.icp = d.icp; state.presets = d.presets; state.stale = d.stale; state.icpDraft = clone(d.icp);
    const sel = $("#preset-select"); sel.innerHTML = "";
    for (const p of d.presets) sel.append(el("option", { value: p.id, selected: p.id === d.icp.id }, `${p.name} — ${p.client}`));
    renderICPForm(); renderStale(d.stale); refreshLive(); loadQuestions();
  }
  const onDraftChange = debounce(() => refreshLive(true), 250);
  function renderICPForm() {
    const f = $("#icp-form"); f.innerHTML = ""; const d = state.icpDraft;
    const bind = (obj, key, input, num = false) => { input.addEventListener("input", () => { obj[key] = num ? parseFloat(input.value) : input.value; onDraftChange(); }); return input; };
    // profile
    const prof = el("div", { class: "card icp-sec" }, el("div", { class: "card-head" }, el("div", {}, el("div", { class: "eyebrow" }, "Profile"), el("h3", {}, d.name))));
    prof.append(el("div", { class: "frow" }, field("ICP name", bind(d, "name", el("input", { value: d.name }))), field("Client", bind(d, "client", el("input", { value: d.client })))));
    prof.append(field("Summary (context for the team, not sent to Jev)", bind(d, "summary", el("textarea", {}, d.summary || ""))));
    prof.append(field("Geography (Jev judges stated locations against this)", bind(d, "geography", el("input", { value: d.geography }))));
    f.append(prof);
    // lists
    f.append(listSection("Industries", "industries", "One Choice question: these options plus `other`. Descriptions are what Jev reads.", false));
    f.append(listSection("Buyer personas", "personas", "One Choice question plus `other`; the weight is how much the persona counts towards fit.", true));
    f.append(listSection("Qualifying pains", "pains", "One yes/no question per pain plus one evidence Choice over the lead's sentences. Add a pain: only its two questions are asked on the next run.", true));
    f.append(listSection("Disqualifiers", "disqualifiers", "One yes/no question each; any above the threshold overrides the tier.", false));
    // firmographics
    const firm = el("div", { class: "card icp-sec" }, el("div", { class: "card-head" }, el("div", {}, el("div", { class: "eyebrow" }, "Firmographics"), el("h3", {}, "Stated only, never inferred"))));
    const bands = el("div", { class: "bands" });
    for (const b of d.size_bands) { const on = d.target_size_bands.includes(b); const lab = el("label", { class: on ? "on" : "" }, el("input", { type: "checkbox", checked: on, hidden: true, onchange: (e) => { d.target_size_bands = d.size_bands.filter((x) => (x === b ? e.target.checked : d.target_size_bands.includes(x))); lab.classList.toggle("on", e.target.checked); onDraftChange(); } }), b); bands.append(lab); }
    firm.append(field("Target team size bands (stated sizes outside these reduce fit by 20%)", bands));
    const rev = el("select", { onchange: (e) => { d.min_revenue_band = e.target.value; onDraftChange(); } });
    for (const b of d.revenue_bands) rev.append(el("option", { value: b, selected: b === d.min_revenue_band }, d.revenue_band_labels[b] || b));
    firm.append(el("div", { class: "frow" }, field("Minimum stated revenue band (below → disqualified)", rev), field("Maturity fit per level 0–4 (pre-revenue → large)", el("input", { value: d.maturity_fit.join(", "), oninput: (e) => { const v = e.target.value.split(",").map((x) => parseFloat(x.trim())); if (v.length === 5 && v.every((x) => !isNaN(x))) { d.maturity_fit = v; onDraftChange(); } } }))));
    f.append(firm);
    // weights + thresholds
    const wt = el("div", { class: "card icp-sec" }, el("div", { class: "card-head" }, el("div", {}, el("div", { class: "eyebrow" }, "Weights & thresholds · code, not questions"), el("h3", {}, "Move a slider: every lead re-scores from cache"))));
    const sl = el("div", { class: "sliders" });
    for (const k of ["industry", "maturity", "persona", "pains"]) sl.append(slider(`fit weight · ${k}`, d.weights, k, 0, 1, 0.05));
    for (const k of Object.keys(d.intent_weights)) sl.append(slider(`intent weight · ${title(k)}`, d.intent_weights, k, 0, 1, 0.05));
    wt.append(sl, el("div", { class: "hint", style: "margin-top:10px" }, "Tier matrix thresholds"));
    const sl2 = el("div", { class: "sliders" });
    for (const k of ["fit_hot", "fit_warm", "intent_hot", "intent_warm", "confidence_floor", "disqualifier_p", "dedupe_p", "pain_p"]) sl2.append(slider(title(k), d.thresholds, k, 0, 1, 0.01));
    wt.append(sl2); f.append(wt);
    // routes
    const rt = el("div", { class: "card icp-sec" }, el("div", { class: "card-head" }, el("div", {}, el("div", { class: "eyebrow" }, "Routes"), el("h3", {}, "Where each tier goes"))));
    for (const t of TIERS) { const r = d.routes[t]; rt.append(el("div", { class: "item two", style: "grid-template-columns: 90px 1fr 1fr" }, el("span", { class: "tpill", "data-tier": t, style: "align-self:center;justify-self:start" }, t), bind(r, "label", el("input", { value: r.label, placeholder: "label" })), bind(r, "owner", el("input", { value: r.owner, placeholder: "owner" })))); }
    f.append(rt);
  }
  const field = (label, input) => el("div", { class: "field" }, el("label", {}, label), input);
  function slider(label, obj, key, min, max, step) {
    const s = el("div", { class: "slider" });
    const lab = el("label", {}, el("span", {}, label), el("b", {}, Number(obj[key]).toFixed(2)));
    const inp = el("input", { type: "range", min, max, step, value: obj[key], oninput: (e) => { obj[key] = parseFloat(e.target.value); lab.lastChild.textContent = obj[key].toFixed(2); onDraftChange(); } });
    s.append(lab, inp); return s;
  }
  function listSection(label, key, hint, weighted) {
    const d = state.icpDraft;
    const card = el("div", { class: "card icp-sec", id: `sec-${key}` });
    const items = el("div", { class: "items" });
    const render = () => {
      items.innerHTML = "";
      for (const [id, v] of Object.entries(d[key])) {
        const isObj = typeof v === "object";
        const row = el("div", { class: `item${weighted ? "" : " two"}` });
        row.append(el("input", { class: "id", value: id, title: "id (slug)", onchange: (e) => { const nid = e.target.value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_"); if (!nid || nid === id) { e.target.value = id; return; } const entries = Object.entries(d[key]).map(([k, x]) => [k === id ? nid : k, x]); d[key] = Object.fromEntries(entries); render(); onDraftChange(); } }));
        row.append(el("textarea", { oninput: (e) => { if (isObj) d[key][id].description = e.target.value; else d[key][id] = e.target.value; onDraftChange(); } }, isObj ? v.description : v));
        if (weighted) row.append(el("input", { type: "number", step: "0.1", min: 0, max: 1, value: v.weight ?? 1, title: "weight", oninput: (e) => { d[key][id].weight = parseFloat(e.target.value) || 0; onDraftChange(); } }));
        row.append(el("button", { class: "del", title: "remove", onclick: () => { delete d[key][id]; render(); onDraftChange(); } }, "×"));
        items.append(row);
      }
    };
    card.append(el("div", { class: "card-head" }, el("div", {}, el("div", { class: "eyebrow" }, label), el("h3", {}, `${Object.keys(d[key]).length} ${label.toLowerCase()}`)),
      el("button", { class: "btn small", onclick: () => { addItem(key, `new_${key.slice(0, -1)}_${Object.keys(d[key]).length + 1}`, "", weighted); render(); items.lastElementChild?.classList.add("new"); items.lastElementChild?.querySelector("textarea")?.focus(); } }, "Add")));
    card.append(el("div", { class: "hint" }, hint), items);
    render();
    card._render = render;
    return card;
  }
  function addItem(key, id, description, weighted, weight = 1.0) {
    state.icpDraft[key][id] = weighted ? { description, weight } : description;
  }
  async function refreshLive(changed = false) {
    const body = $("#icp-live-body");
    if (!Object.keys(state.results).length) { body.className = "muted"; body.textContent = "Run the pipeline once; then every edit here re-scores instantly."; return; }
    let live;
    try { live = await api("/api/rescore", { method: "POST", body: JSON.stringify({ icp: state.icpDraft }) }); }
    catch (e) { body.className = "muted"; body.innerHTML = `<span style="color:var(--red)">${esc(e.message)}</span>`; return; }
    state.liveResults = live.results; renderStale(live.stale, true);
    body.className = ""; body.innerHTML = "";
    const base = state.totals.tiers, now = live.totals.tiers;
    const tiers = el("div", { class: "live-tiers" });
    for (const t of TIERS) { const dlt = now[t] - base[t]; tiers.append(el("div", { class: "live-tier", "data-tier": t }, el("div", { class: "n" }, now[t]), el("div", { class: "k" }, TIER_LABEL[t]), el("div", { class: `d ${dlt > 0 ? "up" : dlt < 0 ? "down" : ""}` }, dlt ? (dlt > 0 ? `+${dlt}` : `${dlt}`) : ""))); }
    body.append(tiers);
    const moves = live.results.filter((r) => state.results[r.lead_id] && state.results[r.lead_id].tier !== r.tier);
    $("#icp-live-pill").textContent = `${live.results.length} leads · from cache · 0 API calls${moves.length ? ` · ${moves.length} moved` : ""}`;
    if (moves.length) {
      const mv = el("div", { class: "moves" });
      for (const r of moves) mv.append(el("div", { class: "move", onclick: () => openLead(r.lead_id) }, el("span", { class: "co" }, state.leadsById[r.lead_id]?.company_name || r.lead_id), el("span", { class: "tpill", "data-tier": state.results[r.lead_id].tier }, state.results[r.lead_id].tier), el("span", { class: "muted" }, "→"), el("span", { class: "tpill", "data-tier": r.tier }, r.tier), el("span", { class: "muted small" }, r.why[r.why.length - 1])));
      body.append(mv);
    } else body.append(el("p", { class: "small muted", style: "margin-top:8px" }, changed ? "No lead changes tier under this edit." : "Saved profile. Edit anything on the left to see tiers move."));
    if (live.metrics) body.append(el("p", { class: "small", style: "margin-top:8px" }, `Tier accuracy vs gold under this draft: `, el("b", {}, pct(live.metrics.tier_accuracy))));
    state.liveMoves = moves;
  }
  function renderStale(stale, draft = false) {
    if (!stale) return;
    const n = stale.questions_to_ask;
    $("#stale-title").textContent = n === 0 ? "Nothing — every answer is cached" : `${n} questions across ${stale.leads} leads`;
    $("#stale-body").innerHTML = n === 0 ? `All ${stale.questions_total} answers for ${stale.cached_leads} leads are cached under the ${draft ? "draft" : "saved"} profile. Threshold and weight edits never need a new request.` :
      `${stale.cached_leads} of ${stale.leads} leads cached · ${stale.questions_total - n} of ${stale.questions_total} answers reusable · new or changed: <span class="mono">${esc((stale.stale_question_ids || []).slice(0, 8).join(", "))}${(stale.stale_question_ids || []).length > 8 ? " …" : ""}</span>${draft ? "<br><b>Save the ICP</b>, then run to ask only these." : ""}`;
    $("#btn-icp-run").hidden = n === 0 || draft;
  }
  $("#btn-icp-save").addEventListener("click", saveICP);
  async function saveICP() {
    const btn = $("#btn-icp-save"); busy(btn, true);
    try {
      const d = await api("/api/icp", { method: "PUT", body: JSON.stringify({ icp: state.icpDraft }) });
      state.icp = d.icp; state.icpDraft = clone(d.icp); renderStale(d.stale);
      await loadStatus(); await loadResults(); renderICPForm(); refreshLive();
      toast(d.stale.questions_to_ask ? `ICP saved — ${d.stale.questions_to_ask} questions would be asked on the next run` : "ICP saved — tiers re-scored from cache, 0 API calls");
      return d;
    } catch (e) { toast(e.message, true); }
    finally { busy(btn, false); }
  }
  $("#btn-icp-run").addEventListener("click", async () => { const r = await run(false); showPage("icp"); await loadICP(true); return r; });
  $("#btn-icp-reset").addEventListener("click", async () => { await api("/api/icp/reset", { method: "POST" }); await loadStatus(); await loadResults(); await loadICP(true); toast("ICP reset to the default preset"); });
  $("#btn-icp-preset").addEventListener("click", async () => {
    const id = $("#preset-select").value; const btn = $("#btn-icp-preset"); busy(btn, true);
    try { await api(`/api/icp/presets/${id}`, { method: "POST" }); await loadStatus(); await loadResults(); await loadICP(true); toast(`Loaded preset — the question set changed; run to score under it`); }
    catch (e) { toast(e.message, true); }
    busy(btn, false);
  });
  async function loadQuestions() {
    const q = await api("/api/questions");
    $("#questions-count").textContent = `— ${q.n} questions for ${q.lead_id} · ${q.crm_candidates.length} CRM candidates`;
    const list = $("#qlist"); list.innerHTML = "";
    for (const g of q.groups) {
      const qs = q.questions.filter((x) => x.group === g); if (!qs.length) continue;
      list.append(el("div", { class: "qgroup" }, `${g} · ${qs.length}`));
      for (const qq of qs) list.append(el("div", { class: "q" }, el("div", {}, el("div", { class: "qid" }, qq.id), el("div", { class: "qt" }, qq.type)), el("div", {}, el("div", {}, qq.text), qq.type !== "noul" ? el("div", { class: "qopts" }, `${qq.n_options} ${qq.type === "score" ? "levels" : "options"}${qq.type === "choice" ? ": " + qq.options.slice(0, 6).join(" · ") + (qq.options.length > 6 ? " · …" : "") : ""}`) : null)));
    }
  }
  $("#questions-toggle").addEventListener("click", () => { const t = $("#questions-toggle"); t.setAttribute("aria-expanded", t.getAttribute("aria-expanded") === "true" ? "false" : "true"); });

  // ------------------------------------------------------------------ accuracy
  function renderAccuracy() {
    const m = state.metrics;
    const has = m && m.n;
    $("#acc-empty").hidden = !!has; $("#acc-kpis").hidden = !has; $("#acc-grid").hidden = !has; $("#acc-errors-card").hidden = !has;
    if (!has) { $("#acc-empty").textContent = state.icp && state.icp.id !== state.status?.default_icp ? "Gold labels exist only for the default ICP (Marketing agencies & coaches). Load it to compare." : "Run the pipeline under the default ICP to compare against the gold labels."; return; }
    const k = $("#acc-kpis"); k.innerHTML = "";
    const kpi = (label, value, ctx, cls = "") => el("div", { class: `kpi ${cls}` }, el("div", { class: "label" }, label), el("div", { class: "value", html: value }), el("div", { class: "ctx" }, ctx));
    k.append(kpi("Tier accuracy", pct(m.tier_accuracy), `${m.n} leads vs gold`, "accent"), kpi("Adjacent-tier", pct(m.tier_accuracy_adjacent), "hot↔warm, warm↔nurture counted"),
      kpi("Persona", pct(m.persona_accuracy), `n = ${m.persona_n}`), kpi("Primary pain", pct(m.pain_accuracy), `n = ${m.pain_n}`),
      kpi("Auto-routed", `${pct(m.by_confidence.auto.tier_accuracy)} <small>· ${m.by_confidence.auto.n}</small>`, "accuracy where no human was asked"),
      kpi("Flagged for a human", `${pct(m.by_confidence.review.tier_accuracy)} <small>· ${m.by_confidence.review.n}</small>`, "low confidence or borderline"));
    const cm = $("#cm"); cm.innerHTML = "";
    const tbl = el("table", { class: "cm" }, el("thead", {}, el("tr", {}, el("th", { class: "row" }, "gold \\ predicted"), ...TIERS.map((t) => el("th", {}, t)))));
    const tb = el("tbody");
    for (const g of TIERS) tb.append(el("tr", {}, el("th", { class: "row" }, g), ...TIERS.map((p) => { const v = m.confusion[g][p]; return el("td", { class: v === 0 ? "zero" : g === p ? "diag" : "off" }, v); })));
    tbl.append(tb); cm.append(tbl);
    const pt = $("#per-tier"); pt.innerHTML = "";
    const t2 = el("table", { class: "cm" }, el("thead", {}, el("tr", {}, el("th", { class: "row" }, "tier"), el("th", {}, "gold"), el("th", {}, "predicted"), el("th", {}, "precision"), el("th", {}, "recall"))));
    const tb2 = el("tbody");
    for (const t of TIERS) { const r = m.per_tier[t]; tb2.append(el("tr", {}, el("th", { class: "row" }, el("span", { class: "tpill", "data-tier": t }, t)), el("td", {}, r.gold), el("td", {}, r.predicted), el("td", {}, r.precision === null ? "—" : pct(r.precision)), el("td", {}, r.recall === null ? "—" : pct(r.recall)))); }
    t2.append(tb2); pt.append(t2);
    $("#err-title").textContent = m.errors.length ? `${m.errors.length} tier misses` : "No tier misses";
    const er = $("#errors"); er.innerHTML = "";
    if (!m.errors.length) er.append(el("p", { class: "small muted" }, "Every lead landed in its gold tier on this run. Repeat runs vary by about ±1 lead near the thresholds; those leads carry the “needs a human” flag."));
    for (const e of m.errors) er.append(el("div", { class: "err", onclick: () => openLead(e.lead_id) }, el("span", { class: "id" }, e.lead_id), el("span", {}, `${state.leadsById[e.lead_id]?.company_name || ""} — gold `, el("span", { class: "tpill", "data-tier": e.gold }, e.gold), " → ", el("span", { class: "tpill", "data-tier": e.predicted }, e.predicted), el("div", { class: "w" }, `${e.why[0] || ""}${e.note ? " · " + e.note : ""}`)), el("span", { class: `conf ${e.needs_review ? "low" : "high"}` }, e.needs_review ? "flagged" : "auto")));
  }

  // ------------------------------------------------------------------ explore
  function fillFilters() {
    const rs = Object.values(state.results);
    const opts = (sel, values, label) => { const cur = sel.value; sel.innerHTML = `<option value="">${label}</option>`; for (const v of values) sel.append(el("option", { value: v }, title(v))); sel.value = cur; };
    opts($("#f-industry"), [...new Set(rs.map((r) => r.components.industry.choice).filter(Boolean))].sort(), "All industries");
    opts($("#f-persona"), [...new Set(rs.map((r) => r.components.persona.choice).filter(Boolean))].sort(), "All personas");
    opts($("#f-pain"), Object.keys(state.icp?.pains || {}), "All pains");
    opts($("#f-tier"), TIERS, "All tiers");
  }
  ["f-industry", "f-persona", "f-pain", "f-tier"].forEach((id) => $(`#${id}`).addEventListener("change", renderExplore));
  function renderExplore() {
    const rs = Object.values(state.results);
    if (!state.icp) { api("/api/icp").then((d) => { state.icp = d.icp; state.presets = d.presets; renderExplore(); }); return; }
    fillFilters();
    const fi = $("#f-industry").value, fp = $("#f-persona").value, fpa = $("#f-pain").value, ft = $("#f-tier").value;
    const t = state.icp.thresholds;
    const match = (r) => (!fi || r.components.industry.choice === fi) && (!fp || r.components.persona.choice === fp) && (!fpa || (r.components.pains.scores[fpa] || 0) >= t.pain_p) && (!ft || r.tier === ft);
    const sel = rs.filter(match);
    $("#scatter-title").textContent = rs.length ? `${sel.length} of ${rs.length} leads${fi || fp || fpa || ft ? " match the filter" : ""}` : "Run the pipeline to populate";
    const lg = $("#scatter-legend"); lg.innerHTML = ""; for (const tt of TIERS) lg.append(el("span", { class: `lg ${tt}` }, TIER_LABEL[tt]));
    const W = 640, H = 420, pl = 44, pb = 34, pt = 14, pr = 14;
    const x = (v) => pl + v * (W - pl - pr), y = (v) => H - pb - v * (H - pb - pt);
    const svg = svgel("svg", { viewBox: `0 0 ${W} ${H}` });
    for (const v of [0, .25, .5, .75, 1]) { svg.append(svgel("line", { class: "grid", x1: x(v), x2: x(v), y1: y(0), y2: y(1) }), svgel("line", { class: "grid", x1: x(0), x2: x(1), y1: y(v), y2: y(v) })); svg.append(svgel("text", { class: "lbl", x: x(v), y: H - pb + 14, "text-anchor": "middle" }, v.toFixed(2)), svgel("text", { class: "lbl", x: pl - 6, y: y(v) + 3, "text-anchor": "end" }, v.toFixed(2))); }
    for (const v of [t.fit_warm, t.fit_hot]) svg.append(svgel("line", { class: "axis", x1: x(v), x2: x(v), y1: y(0), y2: y(1), "stroke-dasharray": "4 4" }));
    for (const v of [t.intent_warm, t.intent_hot]) svg.append(svgel("line", { class: "axis", x1: x(0), x2: x(1), y1: y(v), y2: y(v), "stroke-dasharray": "4 4" }));
    svg.append(svgel("text", { class: "lbl", x: x(.5), y: H - 4, "text-anchor": "middle" }, "ICP fit →"), svgel("text", { class: "lbl", x: 12, y: y(.5), transform: `rotate(-90 12 ${y(.5)})`, "text-anchor": "middle" }, "intent →"));
    svg.append(svgel("text", { class: "zone", x: x(1) - 4, y: y(1) + 12, "text-anchor": "end" }, "hot: founder call"), svgel("text", { class: "zone", x: x(0) + 4, y: y(0) - 6 }, "nurture: content track"), svgel("text", { class: "zone", x: x(0) + 4, y: y(1) + 12 }, "strong intent, weak fit: a human decides"));
    const C = { hot: "var(--hot)", warm: "var(--warm)", nurture: "var(--nurture)", disqualify: "var(--dq)", existing: "var(--existing)" };
    const tip = $(".tip") || document.body.appendChild(el("div", { class: "tip", hidden: true }));
    for (const r of rs) {
      const lead = state.leadsById[r.lead_id] || {};
      const jit = ((r.lead_id.charCodeAt(3) * 7) % 5 - 2) * 1.2;
      const dot = svgel("circle", { class: `dot${match(r) ? "" : " dim"}`, cx: x(r.fit) + jit, cy: y(r.intent) + jit, r: 6, fill: C[r.tier] });
      dot.addEventListener("mouseenter", (e) => { tip.hidden = false; tip.innerHTML = `<b>${esc(lead.company_name)}</b> · ${r.tier}<br>fit ${r.fit.toFixed(2)} · intent ${r.intent.toFixed(2)}<br>${esc(title(r.components.industry.choice))} · ${esc(title(r.components.persona.choice))}${r.primary_pain ? " · " + esc(title(r.primary_pain)) : ""}`; });
      dot.addEventListener("mousemove", (e) => { tip.style.left = `${e.clientX + 12}px`; tip.style.top = `${e.clientY + 12}px`; });
      dot.addEventListener("mouseleave", () => (tip.hidden = true));
      dot.addEventListener("click", () => { tip.hidden = true; openLead(r.lead_id); });
      svg.append(dot);
    }
    $("#scatter").innerHTML = ""; $("#scatter").append(svg);
    // heatmap: pains × (hot, warm, nurture)
    const heat = $("#heatmap"); heat.innerHTML = "";
    const pains = Object.keys(state.icp.pains);
    const cols = ["hot", "warm", "nurture"];
    const counts = Object.fromEntries(pains.map((p) => [p, Object.fromEntries(cols.map((c) => [c, 0]))]));
    const nTier = Object.fromEntries(cols.map((c) => [c, rs.filter((r) => r.tier === c).length]));
    for (const r of rs) if (cols.includes(r.tier)) for (const p of pains) if ((r.components.pains.scores[p] || 0) >= t.pain_p) counts[p][r.tier]++;
    const grid = el("div", { class: "heat" }, el("div"), ...cols.map((c) => el("div", { class: "hh" }, `${TIER_LABEL[c]} · ${nTier[c]}`)), el("div", { class: "hh" }, "all"));
    const sorted = [...pains].sort((a, b) => counts[b].hot - counts[a].hot || counts[b].warm - counts[a].warm);
    for (const p of sorted) {
      grid.append(el("div", { class: "rn", style: painStyle(p) }, el("span", { class: "chip pain" }, title(p))));
      for (const c of cols) { const v = counts[p][c]; const a = nTier[c] ? v / nTier[c] : 0; grid.append(el("div", { class: "cell", "data-tier": c, style: `--a:${Math.min(1, a * 1.1).toFixed(2)}`, title: `${v} of ${nTier[c]} ${c} leads name ${title(p)}` }, v ? `${v} · ${Math.round(a * 100)}%` : "·")); }
      grid.append(el("div", { class: "tot" }, cols.reduce((s, c) => s + counts[p][c], 0)));
    }
    heat.append(grid);
    const top = sorted[0]; const hotN = nTier.hot;
    $("#heat-line").textContent = rs.length && hotN ? `${counts[top].hot} of ${hotN} Hot leads name “${title(top)}” — that is the headline for the client's ads and landing page.${sorted[1] && counts[sorted[1]].hot ? ` “${title(sorted[1])}” is second with ${counts[sorted[1]].hot}.` : ""}` : "";
    state.heatTop = rs.length ? { pain: top, hot: counts[top]?.hot, hotN } : null;
  }

  // ------------------------------------------------------------------ connect
  const INPUTS = [["W", "Website forms", "Webhook from Typeform, Webflow, HubSpot forms or a plain HTML form — message + page context"], ["I", "Instantly · Apollo replies", "Reply webhooks from cold-email tools; the thread is the message, the export row is the profile"], ["L", "LinkedIn exports & DMs", "CSV exports of connections or Sales Navigator lists; DMs pasted or forwarded"], ["M", "Shared inbox (IMAP)", "hello@ / sales@ read-only; nothing marked as read"]];
  const OUTPUTS = [["H", "HubSpot", "Hand off a Hot lead: tier, route, fit, intent, primary pain and next action go on a test contact (or a note on an existing company). Off until HubSpot write is switched on."], ["C", "Founder calendar", "Hot leads get two proposed slots (Cal.com / Calendly link) in the draft reply"], ["S", "SDR sequence A", "Warm leads enrolled in a 3-step sequence with the matching case study"], ["N", "Nurture & decline drafts", "Nurture list for the newsletter tool; decline templates saved as drafts, never auto-sent"]];
  function renderConnect() {
    const inp = $("#connect-inputs"); inp.innerHTML = ""; for (const [ic, nm, ds] of INPUTS) inp.append(el("div", { class: "connector" }, el("span", { class: "ic" }, ic), el("div", {}, el("div", { class: "nm" }, nm), el("div", { class: "ds" }, ds)), el("span", { class: "pill" }, "webhook · CSV")));
    const out = $("#connect-outputs"); out.innerHTML = ""; for (const [ic, nm, ds] of OUTPUTS) out.append(el("div", { class: "connector" }, el("span", { class: "ic" }, ic), el("div", {}, el("div", { class: "nm" }, nm), el("div", { class: "ds" }, ds)), el("span", { class: "pill" }, "API")));
    const s = state.status || {};
    const ap = s.apollo || {}; const pill = $("#apollo-pill"); pill.className = "pill " + (ap.enabled ? "good" : ""); pill.textContent = ap.enabled ? `enabled · ${ap.cached} cached` : ap.has_key ? "key present · flag off (APOLLO_ENRICH=1)" : "off — no key";
    $("#btn-apollo").disabled = !ap.enabled;
    const kv = $("#connect-kv"); kv.innerHTML = "";
    kv.append(kvNode("Model", s.model, "mono"), kvNode("Endpoint", "api.typesafe.ai/v1/systemone", "mono"), kvNode("API key", s.jev_key ? "set (server-side only)" : "missing"), kvNode("Price", `$${s.price_per_m} / M input tokens · output free`), kvNode("Answers cached", `${s.cache?.leads ?? 0} leads · ${s.cache?.requests ?? 0} requests`), kvNode("Workers", `${s.workers} parallel requests`));
  }
  $("#btn-apollo").addEventListener("click", async () => {
    const btn = $("#btn-apollo"); busy(btn, true); const out = $("#apollo-result"); out.innerHTML = "";
    try {
      const r = await api("/api/apollo/enrich", { method: "POST", body: JSON.stringify({ domain: $("#apollo-domain").value }) });
      if (!r.ok) out.append(el("p", { class: "muted" }, `Not enriched: ${r.reason}`));
      else { const o = r.organization; out.append(el("div", { class: "apollo-org" }, el("b", {}, o.name || r.domain), el("div", { class: "muted" }, [o.industry, o.employees ? `${o.employees} employees` : null, o.city, o.country, o.founded ? `founded ${o.founded}` : null, o.revenue].filter(Boolean).join(" · ")), el("p", { class: "small", style: "margin-top:6px" }, o.description || ""), el("div", { class: "muted small" }, `${r.cached ? "cached" : "live"} · ${(o.keywords || []).slice(0, 8).join(", ")}`))); }
    } catch (e) { toast(e.message, true); }
    busy(btn, false);
  });
  $("#btn-jev-test").addEventListener("click", async () => {
    const btn = $("#btn-jev-test"); busy(btn, true);
    try { const r = await api("/api/jev/test"); $("#jev-test-meta").textContent = `${r.model} · ${r.latency_ms} ms · ${r.input_tokens} tokens · P(asks for meeting) = ${(r.asks_for_meeting ?? 0).toFixed(2)}`; toast(`Jev answered in ${r.latency_ms} ms`); }
    catch (e) { toast(e.message, true); }
    busy(btn, false);
  });

  async function sendCommand(kind) {
    if (!state.currentLead) return;
    try {
      const d = await api(`/api/leads/${state.currentLead}/command`, { method: "POST", body: JSON.stringify({ kind }) });
      renderLead(d);
      toast(`${kind.replace("_", " ")} · ${d.lead.disposition}`);
      if (state.mode === "reviewing") loadReview();
    } catch (e) { toast(e.message, true); }
  }
  $$("#lead-commands [data-cmd]").forEach((b) => b.addEventListener("click", () => sendCommand(b.dataset.cmd)));

  async function loadReview() {
    const d = await api("/api/review");
    const box = $("#review-list"); if (!box) return;
    box.innerHTML = "";
    if (!d.items.length) { box.append(el("p", { class: "muted" }, "Nothing is held. Score leads that need a human, or press Hold on a lead page.")); return; }
    for (const item of d.items) {
      const lead = item.lead, r = item.result;
      const card = el("div", { class: "card review-item", onclick: () => openLead(lead.id) });
      card.append(el("div", { class: "card-head" }, el("div", {}, el("div", { class: "eyebrow" }, lead.disposition), el("h3", {}, `${lead.company_name} — ${lead.person_name}`)), r ? el("span", { class: "tpill", "data-tier": r.tier }, r.tier) : null));
      card.append(el("p", { class: "small muted" }, r ? r.why?.[r.why.length - 1] : "Not scored yet"));
      box.append(card);
    }
  }

  $("#btn-csv")?.addEventListener("click", async () => {
    const btn = $("#btn-csv"); busy(btn, true);
    try {
      const r = await api("/api/imports", { method: "POST", body: JSON.stringify({ csv: $("#csv-text").value }) });
      $("#csv-meta").textContent = `${r.inserted.length} arrived · ${r.skipped.length} already there`;
      await loadLeads(); toast(`CSV: ${r.inserted.length} work items`);
    } catch (e) { toast(e.message, true); }
    busy(btn, false);
  });
  $("#btn-search")?.addEventListener("click", async () => {
    const btn = $("#btn-search"); busy(btn, true);
    try {
      const r = await api("/api/search", { method: "POST", body: JSON.stringify({}) });
      $("#search-meta").textContent = `${r.inserted.length} arrived · ${r.skipped.length} already there · ${r.hits} hits`;
      await loadLeads(); toast(`Search: ${r.inserted.length} work items`);
    } catch (e) { toast(e.message, true); }
    busy(btn, false);
  });

  // ------------------------------------------------------------------ boot
  async function boot() {
    await loadStatus();
    await loadLeads();
    const d = await api("/api/icp"); state.icp = d.icp; state.presets = d.presets; state.stale = d.stale;
    await loadResults();
    renderValue();
    const initial = location.hash.replace("#", "");
    const leadMatch = initial.match(/^lead\/(.+)$/);
    if (leadMatch) openLead(leadMatch[1]);
    else if (["pipeline", "lead", "review", "icp", "accuracy", "explore", "connect"].includes(initial)) showPage(initial);
    const q = new URLSearchParams(location.search);
    if (q.get("lead")) openLead(q.get("lead"));
    if (q.get("run")) run(q.get("run") === "fresh");
    if (q.get("demo")) window.FR.openDemo(true);
  }
  window.FR = { state, session, api, el, esc, usd, pct, title, toast, sleep, TIERS, TIER_LABEL, showPage, run, openLead, loadResults, loadICP, loadStatus, saveICP, refreshLive, renderICPForm, addItem, renderExplore, renderAccuracy, busy };
  boot();
})();
