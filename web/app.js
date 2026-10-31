// AgentAudit single-page UI. No build step, no dependencies.
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pct = (x) => `${Math.round((x || 0) * 100)}%`;

  // Theme ------------------------------------------------------------------
  const setTheme = (t) => { document.documentElement.dataset.theme = t; localStorage.setItem("aa-theme", t); };
  setTheme(localStorage.getItem("aa-theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
  $("#theme").onclick = () => setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");

  // Tabs -------------------------------------------------------------------
  $$(".tab").forEach((t) => (t.onclick = () => {
    $$(".tab").forEach((x) => { x.classList.toggle("active", x === t); x.setAttribute("aria-selected", x === t); });
    $$(".tabpanel").forEach((p) => p.classList.toggle("hidden", p.dataset.panel !== t.dataset.tab));
  }));

  const status = (msg, kind = "") => {
    const el = $("#status");
    if (!msg) return el.classList.add("hidden");
    el.className = `status ${kind}`; el.innerHTML = msg;
  };

  // Judge mode ---------------------------------------------------------------
  async function loadExamples() {
    try {
      const { examples } = await (await fetch("/api/examples")).json();
      $("#examples").innerHTML = examples.map((e) => `
        <button class="example" data-id="${esc(e.id)}">
          <span class="pill v-${esc(e.verdict)}" style="align-self:flex-start">${esc((e.verdict || "").replace(/_/g, " "))}</span>
          <span class="name">${esc(e.agent)}</span>
          <span class="blurb">${esc(e.blurb)}</span>
        </button>`).join("") || `<p class="empty">No recorded examples yet.</p>`;
      $$(".example").forEach((b) => (b.onclick = () => openExample(b.dataset.id)));
    } catch { $("#examples").innerHTML = `<p class="empty">Could not load examples.</p>`; }
  }
  async function openExample(id) {
    status(`<span class="spinner"></span>Loading recorded audit…`);
    const r = await fetch(`/api/examples/${encodeURIComponent(id)}`);
    if (!r.ok) return status("Could not load that example.", "error");
    status(""); render(await r.json(), true);
  }

  // Live audits ----------------------------------------------------------------
  async function runAudit(body, btn) {
    btn.disabled = true;
    status(`<span class="spinner"></span>Auditing with nine Clocked endpoints… this usually takes 10–30 seconds.`);
    try {
      const r = await fetch("/api/audit", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
      status(""); render(data, false);
    } catch (e) { status(esc(e.message), "error"); }
    finally { btn.disabled = false; }
  }
  const precision = () => $("#precision").checked;
  $("#gh-form").onsubmit = (ev) => { ev.preventDefault(); runAudit({ github_url: $("#gh-url").value.trim(), precision: precision() }, ev.submitter || $("#gh-form button")); };
  $("#mf-form").onsubmit = (ev) => { ev.preventDefault(); runAudit({ manifest_yaml: $("#mf-text").value, precision: precision() }, ev.submitter || $("#mf-form .primary")); };
  $("#mf-sample").onclick = () => { $("#mf-text").value = $("#sample-manifest").innerHTML.replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">"); };

  // Rendering -----------------------------------------------------------------
  const val = (v) => (v && typeof v === "object" ? (v.value ?? v.choice ?? v.score) : v);
  const fmt = (v) => {
    if (v === null || v === undefined || v === "") return `<span class="muted">—</span>`;
    if (Array.isArray(v)) return v.length ? v.map(esc).join(", ") : `<span class="muted">—</span>`;
    if (typeof v === "boolean") return v ? "yes" : "no";
    if (typeof v === "number") return v.toFixed(2);
    return esc(v);
  };

  function bars(probs, top, labels = {}) {
    const entries = Object.entries(probs || {}).sort((a, b) => b[1] - a[1]);
    return `<div class="bars">${entries.map(([k, p]) => `
      <div class="bar ${k === top ? "top v-" + esc(k) : ""}">
        <span>${esc(labels[k] || k.replace(/_/g, " "))}</span>
        <span class="track"><span class="fill" style="width:${(p * 100).toFixed(1)}%"></span></span>
        <span class="num">${pct(p)}</span></div>`).join("")}</div>`;
  }

  function highlight(text, spans) {
    const ok = spans.filter((s) => s.start >= 0 && s.end > s.start && s.end <= text.length).sort((a, b) => a.start - b.start);
    let out = "", at = 0;
    for (const s of ok) {
      if (s.start < at) continue; // overlapping spans: keep the first
      out += esc(text.slice(at, s.start)) + `<mark>${esc(text.slice(s.start, s.end))}</mark>`;
      at = s.end;
    }
    return out + esc(text.slice(at));
  }

  const RULE = { guard: "AA001", inspect: "AA002", protect: "AA003", verify: "AA004", supply_chain: "AA005" };

  function findingCard(f, artifacts) {
    const art = artifacts.find((a) => a.path === f.path);
    const spans = (f.evidence || []).filter((e) => e.start >= 0);
    const quotes = (f.evidence || []).slice(0, 4).map((e) => `<li>${esc(e.type ? `[${e.type}] ` : "")}${esc(e.quote)}</li>`).join("");
    const detail = f.detail || {};
    const prob = detail.probability ?? detail.malicious ?? detail.contradicted ?? detail.p_untrusted;
    const targets = f.check === "supply_chain" && (detail.targets || []).length
      ? `<div class="targets">Download / run targets: ${detail.targets.slice(0, 6).map((t) => `<code>${esc(t)}</code>`).join(" ")}</div>` : "";
    return `<div class="finding sev-${esc(f.severity)}">
      <div class="finding-top"><span class="pill sev-${esc(f.severity)}">${esc(f.severity)}</span>
        ${RULE[f.check] ? `<span class="rule">${RULE[f.check]}</span>` : ""}
        <span class="title">${esc(f.title)}</span>
        ${prob !== undefined && prob !== null ? `<span class="muted" title="Endpoint probability">p=${Number(prob).toFixed(3)}</span>` : ""}
        <span class="ep" title="Clocked endpoint that produced this finding">${esc(f.endpoint || f.check)}</span></div>
      <div class="path">${esc(f.path)}</div>
      ${quotes ? `<ul class="quotes">${quotes}</ul>` : ""}${targets}
      ${art && spans.length ? `<details class="source"><summary>Show in source</summary><pre class="src">${highlight(art.text, spans)}</pre></details>` : ""}
    </div>`;
  }

  function render(d, recorded) {
    const v = d.verdict || {};
    const verdict = v.verdict || {}, autonomy = v.autonomy || {}, risk = v.risk_of_acting || {};
    const riskScore = typeof risk.score === "number" ? risk.score : null;
    const riskLevel = riskScore === null ? "—" : (risk.legend || {})[String(Math.round(riskScore))] || riskScore.toFixed(1);
    const findings = d.findings || [];
    const safety = findings.filter((f) => f.group === "safety" && f.severity !== "none");
    const facts = findings.filter((f) => f.group === "facts");
    const record = d.record || {}, extracted = d.facts || {};
    const u = d.usage || {};

    const recordRows = Object.entries(record).map(([k, x]) => `<tr><th>${esc(k.replace(/_/g, " "))}</th><td>${fmt(val(x))}
      ${x && typeof x.confidence === "number" ? ` <span class="muted">(${pct(x.confidence)})</span>` : ""}</td></tr>`).join("");
    const extractRows = Object.entries(extracted).map(([k, x]) => `<tr><th>${esc(k.replace(/_/g, " "))}</th><td>${fmt(val(x))}</td></tr>`).join("");

    $("#report").innerHTML = `
      <div class="report-head">
        <div class="card verdict-card">
          <div class="verdict-title"><h2>${esc(d.agent)}</h2>${recorded ? `<span class="ep">recorded audit</span>` : `<span class="ep">live audit</span>`}</div>
          <div class="row" style="justify-content:space-between;align-items:center">
            <span class="verdict-big v-${esc(verdict.choice)}">${esc((verdict.choice || d.verdict_label || "unknown").replace(/_/g, " "))}</span>
            <span class="ep" title="Governed verdict">Decide /decide</span></div>
          ${bars(verdict.probabilities, verdict.choice)}
          <div class="meta">
            <span>Autonomy: <b>${esc((autonomy.choice || "—").replace(/_/g, " "))}</b> ${autonomy.confidence ? `(${pct(autonomy.confidence)})` : ""}</span>
            <span>Risk of acting: <b>${esc(riskLevel)}</b> ${riskScore !== null ? `(${riskScore.toFixed(2)} / 4)` : ""}</span>
          </div>
          ${riskScore !== null ? `<div class="gauge" aria-label="Risk of acting">${[0, 1, 2, 3, 4].map((i) => `<span class="${i <= Math.round(riskScore) ? "on" : ""}"></span>`).join("")}</div>` : ""}
        </div>
        <div class="card">
          <h3><span class="dot docs"></span>Registry record <span class="ep" style="margin-left:auto">Fill /fill</span></h3>
          <table>${recordRows || `<tr><td class="empty">No record.</td></tr>`}</table>
        </div>
      </div>

      <div class="card group">
        <div class="group-head"><span class="dot safety"></span>Safety findings (${safety.length})
          <span class="muted" style="font-weight:400;margin-left:auto;font-size:13px">Guard · Inspect · Protect · Extract + Decide</span></div>
        ${safety.length ? safety.map((f) => findingCard(f, d.artifacts || [])).join("") : `<p class="empty">No injected instructions, risky scripts, embedded secrets or untrusted setup steps found.</p>`}
      </div>

      <div class="two">
        <div class="card group">
          <div class="group-head"><span class="dot facts"></span>Claims vs. capabilities (${facts.length})
            <span class="ep" style="margin-left:auto">Verify /grounding</span></div>
          ${facts.length ? facts.map((f) => findingCard(f, d.artifacts || [])).join("") : `<p class="empty">No README claim is contradicted by the agent's actual tools.</p>`}
        </div>
        <div class="card group">
          <div class="group-head"><span class="dot facts"></span>Registry: duplicates &amp; reuse</div>
          <div><div class="row" style="justify-content:space-between"><b style="font-size:14px">Overlapping agents</b><span class="ep">Compare /compare</span></div>
            ${(d.duplicates || []).length ? `<ul class="list">${d.duplicates.map((x) => `<li><span class="name">${esc(x.agent)}</span><span class="muted">${esc(x.relation)} · ${pct(x.related)}</span></li>`).join("")}</ul>` : `<p class="empty">No overlapping agents in the registry.</p>`}</div>
          <div><div class="row" style="justify-content:space-between"><b style="font-size:14px">Existing agent for this job</b><span class="ep">Rerank /rerank</span></div>
            ${(d.reuse || []).length ? `<ul class="list">${d.reuse.map((x) => `<li><span class="name">${esc(x.agent)}</span><span class="${x.action === "use" ? "pill v-reuse_existing" : "muted"}">${esc(x.action)} · ${(x.score ?? 0).toFixed(2)}</span></li>`).join("")}</ul>` : `<p class="empty">No registry to search.</p>`}</div>
        </div>
      </div>

      <div class="card">
        <h3><span class="dot docs"></span>Verbatim facts <span class="ep" style="margin-left:auto">Extract /extract</span></h3>
        <table>${extractRows || `<tr><td class="empty">No facts extracted.</td></tr>`}</table>
      </div>

      <div class="toolbar">
        <span class="muted" style="margin-right:auto;font-size:13px">${u.calls ?? 0} Clocked calls · ${Math.round(u.credits_this_report ?? u.credits ?? 0)} credits · ${(d.endpoints_used || []).length} endpoints</span>
        <button class="ghost" id="dl-json">Download JSON</button><button class="ghost" id="dl-md">Download Markdown</button>
      </div>`;
    $("#report").classList.remove("hidden");
    const dl = (name, text, type) => { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([text], { type })); a.download = name; a.click(); };
    $("#dl-json").onclick = () => dl(`${d.agent}.agentaudit.json`, JSON.stringify(d, null, 2), "application/json");
    $("#dl-md").onclick = () => dl(`${d.agent}.agentaudit.md`, d.markdown || "", "text/markdown");
    $("#report").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  loadExamples();
})();
