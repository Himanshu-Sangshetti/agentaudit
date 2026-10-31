/* AgentAudit write-up figures. Every number comes from data.json (computed from per-row records). */
(function () {
  "use strict";
  const DATA = JSON.parse(document.getElementById("aa-data").textContent);
  const EX = JSON.parse(document.getElementById("aa-examples").textContent);
  /* The supply-chain check's credits are not in the row records: 4,474 credits over 244 skills, from
     bench/credit_ledger.jsonl (tag skills-test-supplychain). */
  const SUPPLY_CREDITS = 18.3;
  [DATA.skills, DATA.forest].forEach((rows) => rows.forEach((r) => {
    if (r.arm === "Supply-chain check only") r.credits = SUPPLY_CREDITS;
    if (r.arm === "AgentAudit pipeline") r.credits = r.credits + SUPPLY_CREDITS;
  }));
  const tip = document.getElementById("tip");
  const fmt = (v, d = 1) => (v == null || isNaN(v) ? "—" : (+v).toFixed(d));
  const pct = (v) => fmt(v) + "%";

  /* Categorical slots in fixed order: 1 blue, 2 orange, 3 aqua, 4 yellow. */
  const S = { aa: "var(--aa)", clk: "var(--clk)", base: "var(--base)", neutral: "var(--neutral)" };
  const GROUP = { clocked: S.clk, baseline: S.base, agentaudit: S.aa };
  const ARMCOLOR = {
    "Clocked + AgentAudit policy": S.aa, "Clocked + AgentAudit": S.aa, "AgentAudit pipeline": S.aa,
    "Clocked Guard (default)": S.clk, "Clocked Inspect (default)": S.clk, "Clocked default": S.clk,
    "ProtectAI DeBERTa": S.base, "Supply-chain check": S.aa, "deepset DeBERTa": S.base,
  };
  /* Three hues by family; line style is the secondary encoding within a family. */
  const ARMDASH = { "deepset DeBERTa": "6 4", "Supply-chain check": "6 4", "Clocked Inspect (default)": "6 4" };

  function showTip(evt, html) {
    tip.innerHTML = html;
    tip.style.opacity = 1;
    const pad = 14, w = tip.offsetWidth, h = tip.offsetHeight;
    let x = evt.clientX + pad, y = evt.clientY + pad;
    if (x + w > window.innerWidth - 8) x = evt.clientX - w - pad;
    if (y + h > window.innerHeight - 8) y = evt.clientY - h - pad;
    tip.style.left = x + "px";
    tip.style.top = y + "px";
  }
  const hideTip = () => (tip.style.opacity = 0);
  const width = (el) => Math.max(260, el.clientWidth || el.parentNode.clientWidth || 460);
  const byId = (id) => document.getElementById(id);

  function frame(el, W, H, label) {
    el.innerHTML = "";
    return d3.select(el).append("svg").attr("viewBox", `0 0 ${W} ${H}`).attr("role", "img").attr("aria-label", label);
  }
  function grid(svg, x, y, m, W, H, xt = 5, yt = 5) {
    svg.append("g").attr("class", "grid").selectAll("line.v").data(x.ticks(xt)).join("line")
      .attr("x1", (d) => x(d)).attr("x2", (d) => x(d)).attr("y1", m.t).attr("y2", H - m.b);
    svg.append("g").attr("class", "grid").selectAll("line.h").data(y.ticks(yt)).join("line")
      .attr("y1", (d) => y(d)).attr("y2", (d) => y(d)).attr("x1", m.l).attr("x2", W - m.r);
  }
  function axes(svg, x, y, m, W, H, opt) {
    svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`)
      .call(d3.axisBottom(x).ticks(opt.xt || 5).tickSize(4).tickFormat(opt.xf || null));
    svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`)
      .call(d3.axisLeft(y).ticks(opt.yt || 5).tickSize(4).tickFormat(opt.yf || null));
    if (opt.xl) svg.append("text").attr("class", "note").attr("x", (m.l + W - m.r) / 2).attr("y", H - 4).attr("text-anchor", "middle").text(opt.xl);
    if (opt.yl) svg.append("text").attr("class", "note").attr("transform", `translate(11,${(m.t + H - m.b) / 2}) rotate(-90)`).attr("text-anchor", "middle").text(opt.yl);
    if (opt.title) svg.append("text").attr("class", "panel-title").attr("x", 0).attr("y", 13).text(opt.title);
  }

  /* Line chart: ROC, sweeps, reliability. Direct labels at line ends; hover shows nearest point. */
  function lines(el, series, opt) {
    const W = width(el), sq = opt.square ? Math.min(W, 520) : W;
    const H = opt.square ? Math.round(sq * 0.9) : (opt.height || 260);
    const m = { t: 24, r: opt.labelRoom || 16, b: 38, l: 44 };
    const svg = frame(el, W, H, opt.title);
    const x = d3.scaleLinear().domain(opt.xd || [0, 1]).range([m.l, W - m.r]);
    const y = d3.scaleLinear().domain(opt.yd || [0, 1]).range([H - m.b, m.t]);
    grid(svg, x, y, m, W, H);
    axes(svg, x, y, m, W, H, opt);
    if (opt.chance) svg.append("line").attr("x1", x(0)).attr("y1", y(0)).attr("x2", x(0.4)).attr("y2", y(0.4)).style("stroke", "var(--ink-3)").style("stroke-dasharray", "4 4");
    if (opt.diagonal) svg.append("line").attr("x1", x(opt.xd ? opt.xd[0] : 0)).attr("y1", y(opt.yd ? opt.yd[0] : 0)).attr("x2", x(opt.xd ? opt.xd[1] : 1)).attr("y2", y(opt.yd ? opt.yd[1] : 1))
      .style("stroke", "var(--ink-3)").style("stroke-dasharray", "4 4");
    if (opt.vline != null) {
      svg.append("line").attr("x1", x(opt.vline)).attr("x2", x(opt.vline)).attr("y1", m.t).attr("y2", H - m.b).style("stroke", "var(--ink-3)").style("stroke-dasharray", "3 3");
      svg.append("text").attr("class", "note").attr("x", x(opt.vline) + 4).attr("y", m.t + 10).text(opt.vlabel || "");
    }
    const line = d3.line().x((p) => x(p.x)).y((p) => y(p.y)).curve(opt.step ? d3.curveStepAfter : d3.curveLinear);
    series.forEach((s) => {
      svg.append("path").attr("d", line(s.points)).style("fill", "none").style("stroke", s.color).style("stroke-width", s.thin ? 1.2 : 2)
        .style("stroke-dasharray", s.dash || null).style("opacity", s.thin ? 0.45 : 1);
      if (s.dots) s.points.forEach((p) => svg.append("circle").attr("cx", x(p.x)).attr("cy", y(p.y)).attr("r", p.r || 4)
        .style("fill", s.color).style("stroke", "var(--paper)").style("stroke-width", 1.5).style("opacity", 0.9));
    });
    (opt.labels || []).forEach((l) => {
      svg.append("text").attr("class", "lab").attr("x", x(l.x) + (l.dx || 6)).attr("y", y(l.y) + (l.dy || 4))
        .attr("text-anchor", l.anchor || "start").style("font-size", "11.5px").text(l.text);
    });
    (opt.markers || []).forEach((mk) => {
      const g = svg.append("g").attr("transform", `translate(${x(mk.x)},${y(mk.y)})`);
      if (mk.shape === "diamond") g.append("path").attr("d", d3.symbol(d3.symbolDiamond, 90)()).style("fill", mk.fill || "var(--paper)").style("stroke", mk.color).style("stroke-width", 2);
      else if (mk.shape === "square") g.append("rect").attr("x", -5).attr("y", -5).attr("width", 10).attr("height", 10).style("fill", mk.fill || "var(--paper)").style("stroke", mk.color).style("stroke-width", 2);
      else g.append("circle").attr("r", 6).style("fill", mk.fill || "var(--paper)").style("stroke", mk.color).style("stroke-width", 2.2);
      if (mk.text) svg.append("text").attr("class", "lab").attr("x", x(mk.x) + (mk.dx || 9)).attr("y", y(mk.y) + (mk.dy || 4)).attr("text-anchor", mk.anchor || "start").style("font-size", "11px").text(mk.text);
      g.append("circle").attr("r", 12).attr("class", "hit").on("mousemove", (e) => showTip(e, mk.tip)).on("mouseleave", hideTip);
    });
    // nearest-point hover over the plot
    const all = [];
    series.forEach((s) => s.points.forEach((p) => all.push({ s, p })));
    const delaunay = d3.Delaunay.from(all, (d) => x(d.p.x), (d) => y(d.p.y));
    const focus = svg.append("circle").attr("r", 4.5).style("fill", "none").style("stroke", "var(--ink)").style("stroke-width", 1.5).style("opacity", 0);
    svg.append("rect").attr("class", "hit").attr("x", m.l).attr("y", m.t).attr("width", W - m.l - m.r).attr("height", H - m.t - m.b).lower()
      .on("mousemove", (e) => {
        const [mx, my] = d3.pointer(e);
        const d = all[delaunay.find(mx, my)];
        if (!d) return;
        focus.attr("cx", x(d.p.x)).attr("cy", y(d.p.y)).style("opacity", 1);
        showTip(e, opt.tip(d.s, d.p));
      })
      .on("mouseleave", () => { focus.style("opacity", 0); hideTip(); });
    svg.selectAll(".hit").raise();
  }

  /* Dot-and-interval rows (forest plot, per-source FPR, scope pairs). */
  function dots(el, rows, opt) {
    const W = width(el), narrow = W < 520;
    const labelW = narrow ? 0 : (opt.labelW || 230);
    const rowH = narrow ? 40 : 24, m = { t: 26, b: 34, r: 56 };
    let H = m.t + m.b, ys = [];
    rows.forEach((r) => { if (r.header) H += 28; ys.push(H - m.b); H += r.header ? 0 : rowH; });
    const svg = frame(el, W, H, opt.title);
    const x = d3.scaleLinear().domain(opt.xd).range([labelW + 8, W - m.r]);
    svg.append("g").attr("class", "grid").selectAll("line").data(x.ticks(6)).join("line").attr("x1", (d) => x(d)).attr("x2", (d) => x(d)).attr("y1", m.t).attr("y2", H - m.b);
    svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(6).tickSize(4).tickFormat((d) => d + (opt.unit || "")));
    if (opt.title) svg.append("text").attr("class", "panel-title").attr("x", 0).attr("y", 13).text(opt.title);
    if (opt.xl) svg.append("text").attr("class", "note").attr("x", (labelW + W - m.r) / 2).attr("y", H - 4).attr("text-anchor", "middle").text(opt.xl);
    if (opt.ref != null) {
      svg.append("line").attr("x1", x(opt.ref)).attr("x2", x(opt.ref)).attr("y1", m.t).attr("y2", H - m.b).style("stroke", "var(--ink-3)").style("stroke-dasharray", "3 3");
      svg.append("text").attr("class", "note").attr("x", x(opt.ref) + 4).attr("y", m.t + 10).text(opt.refLabel || "");
    }
    rows.forEach((r, i) => {
      const y0 = ys[i];
      if (r.header) {
        svg.append("text").attr("class", "panel-title").attr("x", 0).attr("y", y0 - 4).text(r.header);
        svg.append("line").attr("x1", 0).attr("x2", W - 10).attr("y1", y0 + 2).attr("y2", y0 + 2).style("stroke", "var(--rule)");
        return;
      }
      const cy = narrow ? y0 + 28 : y0 + rowH / 2;
      const label = narrow ? svg.append("text").attr("class", "lab").attr("x", 0).attr("y", y0 + 12) :
        svg.append("text").attr("class", "lab").attr("x", labelW - 6).attr("y", cy + 4).attr("text-anchor", "end");
      label.style("font-size", "12px").text(r.label);
      const c = r.color || GROUP[r.group] || S.neutral;
      if (r.ci) svg.append("line").attr("x1", x(r.ci[0])).attr("x2", x(r.ci[1])).attr("y1", cy).attr("y2", cy).style("stroke", c).style("stroke-width", 2.2).style("opacity", 0.75);
      const shape = r.shape || "circle";
      if (shape === "square") svg.append("rect").attr("x", x(r.v) - 5).attr("y", cy - 5).attr("width", 10).attr("height", 10).attr("rx", 1.5).style("fill", c).style("stroke", "var(--paper)").style("stroke-width", 1.5);
      else svg.append("circle").attr("cx", x(r.v)).attr("cy", cy).attr("r", 5.5).style("fill", r.hollow ? "var(--paper)" : c).style("stroke", r.hollow ? c : "var(--paper)").style("stroke-width", r.hollow ? 2 : 1.5);
      svg.append("text").attr("class", "val").attr("x", W - m.r + 8).attr("y", cy + 4).text(fmt(r.v));
      svg.append("rect").attr("class", "hit").attr("x", 0).attr("y", cy - rowH / 2).attr("width", W).attr("height", rowH)
        .on("mousemove", (e) => showTip(e, r.tip)).on("mouseleave", hideTip);
    });
  }

  /* Strip plot of probabilities, benign vs attack, one band per (policy, label). */
  function strips(el, rows, opt) {
    const W = width(el), m = { t: 24, b: 36, l: opt.labelW || 150, r: 16 };
    const bands = opt.bands, bandH = 40, H = m.t + bands.length * bandH + m.b;
    const svg = frame(el, W, H, opt.title);
    const x = d3.scaleLinear().domain([0, 1]).range([m.l, W - m.r]);
    svg.append("g").attr("class", "grid").selectAll("line").data(x.ticks(5)).join("line").attr("x1", (d) => x(d)).attr("x2", (d) => x(d)).attr("y1", m.t).attr("y2", H - m.b);
    svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(5).tickSize(4));
    svg.append("text").attr("class", "note").attr("x", (m.l + W - m.r) / 2).attr("y", H - 4).attr("text-anchor", "middle").text("Guard injection probability");
    if (opt.title) svg.append("text").attr("class", "panel-title").attr("x", 0).attr("y", 13).text(opt.title);
    svg.append("line").attr("x1", x(0.5)).attr("x2", x(0.5)).attr("y1", m.t).attr("y2", H - m.b).style("stroke", "var(--ink-3)").style("stroke-dasharray", "3 3");
    svg.append("text").attr("class", "note").attr("x", x(0.5)).attr("y", m.t - 4).attr("text-anchor", "middle").text("0.5");
    const rng = d3.randomLcg(42);
    bands.forEach((b, i) => {
      const y0 = m.t + i * bandH, cy = y0 + bandH / 2;
      if (i > 0 && bands[i - 1].policy !== b.policy) svg.append("line").attr("x1", 0).attr("x2", W).attr("y1", y0).attr("y2", y0).style("stroke", "var(--rule)");
      svg.append("text").attr("class", "lab").attr("x", m.l - 10).attr("y", cy - 2).attr("text-anchor", "end").style("font-size", "12px").text(b.label);
      svg.append("text").attr("class", "note").attr("x", m.l - 10).attr("y", cy + 11).attr("text-anchor", "end").text(b.sub);
      const pts = rows.filter((r) => r.label === b.y);
      const atk = b.attack != null ? b.attack : b.y === 1;
      const flagged = pts.filter((r) => r[b.key] >= 0.5).length;
      pts.forEach((r) => {
        const jy = cy + (rng() - 0.5) * (bandH - 14);
        svg.append("circle").attr("cx", x(r[b.key])).attr("cy", jy).attr("r", 2.6)
          .style("fill", atk ? "var(--ink)" : b.color).style("opacity", atk ? 0.5 : 0.75);
      });
      svg.append("rect").attr("class", "hit").attr("x", m.l).attr("y", y0).attr("width", W - m.l - m.r).attr("height", bandH)
        .on("mousemove", (e) => showTip(e, `<b>${b.label}</b> · ${b.sub}<br>${pts.length} rows; <b>${flagged}</b> score ≥ 0.5 (${pct(100 * flagged / pts.length)})<br><span class="k">${atk ? "attacks: higher is better" : "legitimate tools: lower is better"}</span>`))
        .on("mouseleave", hideTip);
    });
  }

  /* Latency ranges: p10–p90 line, p25–p75 box, p50 tick. */
  function latency(el) {
    const rows = DATA.latency, W = width(el), narrow = W < 430, labelW = narrow ? 70 : 190, rowH = 30, m = { t: 26, b: 36, r: narrow ? 62 : 40 };
    const H = m.t + rows.length * rowH + m.b;
    const svg = frame(el, W, H, "Latency");
    const x = d3.scaleLinear().domain([0, d3.max(rows, (r) => r.p90) * 1.1]).range([labelW, W - m.r]);
    svg.append("g").attr("class", "grid").selectAll("line").data(x.ticks(5)).join("line").attr("x1", (d) => x(d)).attr("x2", (d) => x(d)).attr("y1", m.t).attr("y2", H - m.b);
    svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(narrow ? 3 : 5).tickSize(4).tickFormat((d) => d + " ms"));
    svg.append("text").attr("class", "panel-title").attr("x", 0).attr("y", 13).text("Round-trip latency per call");
    rows.forEach((r, i) => {
      const cy = m.t + i * rowH + rowH / 2;
      svg.append("text").attr("class", "lab").attr("x", labelW - 10).attr("y", cy + 4).attr("text-anchor", "end").style("font-size", "12px").text(narrow ? r.endpoint.split(" ")[0] : r.endpoint);
      svg.append("line").attr("x1", x(r.p10)).attr("x2", x(r.p90)).attr("y1", cy).attr("y2", cy).style("stroke", "var(--ink-3)").style("stroke-width", 1.5);
      svg.append("rect").attr("x", x(r.p25)).attr("y", cy - 7).attr("width", x(r.p75) - x(r.p25)).attr("height", 14).attr("rx", 3).style("fill", "var(--soft)").style("stroke", "var(--ink-2)");
      svg.append("line").attr("x1", x(r.p50)).attr("x2", x(r.p50)).attr("y1", cy - 8).attr("y2", cy + 8).style("stroke", "var(--ink)").style("stroke-width", 2.2);
      svg.append("text").attr("class", "val").attr("x", x(r.p90) + 6).attr("y", cy + 4).text(r.p50 + " ms");
      svg.append("rect").attr("class", "hit").attr("x", 0).attr("y", cy - rowH / 2).attr("width", W).attr("height", rowH)
        .on("mousemove", (e) => showTip(e, `<b>${r.endpoint}</b> (n = ${r.n})<br>median <b>${r.p50} ms</b><br><span class="k">p10 ${r.p10} · p25 ${r.p25} · p75 ${r.p75} · p90 ${r.p90}</span>`)).on("mouseleave", hideTip);
    });
  }

  /* Cost vs accuracy scatter (credits per row vs balanced accuracy). */
  function cost(el) {
    const rows = DATA.forest.map((r) => Object.assign({}, r, { credits: r.credits == null ? 0 : r.credits })), W = width(el), H = 300, m = { t: 24, r: 20, b: 40, l: 46 };
    const svg = frame(el, W, H, "Cost versus accuracy");
    const x = d3.scaleLinear().domain([-1, 32]).range([m.l, W - m.r]);
    const y = d3.scaleLinear().domain([50, 100]).range([H - m.b, m.t]);
    grid(svg, x, y, m, W, H);
    axes(svg, x, y, m, W, H, { title: "Credits per row against balanced accuracy", xl: "Clocked credits per row (local baselines = 0)", yl: "Balanced accuracy %", yf: (d) => d });
    const shape = { "Tool poisoning (test)": d3.symbolCircle, "Real-world tools (external)": d3.symbolSquare, "Scripts (test)": d3.symbolTriangle, "Malicious skills (test)": d3.symbolDiamond };
    rows.forEach((r) => {
      const c = GROUP[r.group] || S.neutral;
      svg.append("path").attr("transform", `translate(${x(r.credits)},${y(r.bacc)})`).attr("d", d3.symbol(shape[r.suite] || d3.symbolCircle, 70)())
        .style("fill", c).style("stroke", "var(--paper)").style("stroke-width", 1.2).style("opacity", 0.92);
      svg.append("circle").attr("cx", x(r.credits)).attr("cy", y(r.bacc)).attr("r", 10).attr("class", "hit")
        .on("mousemove", (e) => showTip(e, `<b>${r.arm}</b><br>${r.suite}<br>BAcc <b>${pct(r.bacc)}</b> · ${r.credits ? fmt(r.credits) + " credits/row" : "local, 0 credits"}` + (r.median_ms ? ` · ${Math.round(r.median_ms)} ms` : "")))
        .on("mouseleave", hideTip);
    });
    const lg = svg.append("g").attr("transform", `translate(${W - m.r - 190},${H - m.b - 74})`);
    Object.entries(shape).forEach(([k, sym], i) => {
      lg.append("path").attr("transform", `translate(6,${i * 16 + 6})`).attr("d", d3.symbol(sym, 50)()).style("fill", "var(--ink-3)");
      lg.append("text").attr("x", 16).attr("y", i * 16 + 10).style("font-size", "11px").text(k);
    });
  }

  /* Step chart (ablation waterfall). */
  function steps(el, s, opt) {
    const W = width(el), labelW = Math.min(200, W * 0.4), rowH = 30, m = { t: 26, b: 30 }, H = m.t + s.length * rowH + m.b;
    const svg = frame(el, W, H, opt.title);
    const x = d3.scaleLinear().domain([0, opt.max]).range([labelW, W - 110]);
    svg.append("text").attr("class", "panel-title").attr("x", 0).attr("y", 13).text(opt.title);
    svg.append("g").attr("class", "grid").selectAll("line").data(x.ticks(5)).join("line").attr("x1", (d) => x(d)).attr("x2", (d) => x(d)).attr("y1", m.t - 4).attr("y2", H - m.b + 4);
    svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b + 4})`).call(d3.axisBottom(x).ticks(5).tickSize(4).tickFormat((d) => d + "%"));
    s.forEach((d, i) => {
      const by = m.t + i * rowH + 6, bh = 16, lo = Math.min(d.from, d.to), hi = Math.max(d.from, d.to), total = d.from === 0;
      svg.append("text").attr("class", "lab").attr("x", labelW - 10).attr("y", by + 12).attr("text-anchor", "end").style("font-size", "12px").text(d.label);
      svg.append("rect").attr("x", x(lo)).attr("y", by).attr("height", bh).attr("rx", 3).attr("width", Math.max(2, x(hi) - x(lo))).style("fill", d.color).style("opacity", total ? 1 : 0.55);
      if (i > 0) svg.append("line").attr("x1", x(s[i - 1].to)).attr("x2", x(s[i - 1].to)).attr("y1", by - rowH + bh).attr("y2", by).style("stroke", "var(--ink-3)").style("stroke-dasharray", "2 2");
      const t = total ? fmt(d.to) : (d.to - d.from >= 0 ? "+" : "−") + fmt(Math.abs(d.to - d.from)) + " → " + fmt(d.to);
      svg.append("text").attr("class", "val").attr("x", x(hi) + 6).attr("y", by + 12).text(t);
      svg.append("rect").attr("class", "hit").attr("x", 0).attr("y", by - 6).attr("width", W).attr("height", rowH)
        .on("mousemove", (e) => showTip(e, `<b>${d.label}</b><br>${opt.metricName}: <b>${pct(d.to)}</b>`)).on("mouseleave", hideTip);
    });
  }

  /* Governance heatmap with outlined leave-one-out diagonal. */
  function heatmap(el) {
    const G = DATA.governance, defects = G.defects;
    const names = { poisoned_tool: "Poisoned tool", malicious_script: "Malicious script", embedded_secret: "Embedded secret", duplicate: "Duplicate agent", none: "Clean agent" };
    const diag = { loo_injection: "poisoned_tool", loo_script: "malicious_script", loo_pii: "embedded_secret", loo_compare: "duplicate" };
    const rows = G.rows, W = width(el), narrow = W < 560;
    const labelW = narrow ? 112 : 210, accW = narrow ? 46 : 66, top = narrow ? 30 : 52;
    const cellW = (W - labelW - accW) / defects.length, cellH = 30, H = top + rows.length * cellH + 8;
    const color = d3.scaleQuantize().domain([0, 1]).range(["var(--seq-0)", "var(--seq-1)", "var(--seq-2)", "var(--seq-3)", "var(--seq-4)"]);
    const svg = frame(el, W, H, "Governance heatmap");
    const shortN = { poisoned_tool: "Poison", malicious_script: "Script", embedded_secret: "Secret", duplicate: "Dupe", none: "Clean" };
    defects.forEach((d, j) => (narrow ? [shortN[d]] : names[d].split(" ")).forEach((w, k) => svg.append("text").attr("x", labelW + j * cellW + cellW / 2).attr("y", (narrow ? top - 13 : top - 26) + k * 13)
      .attr("text-anchor", "middle").attr("class", "lab").style("font-size", narrow ? "10.5px" : "12px").text(w)));
    svg.append("text").attr("x", W - accW / 2).attr("y", top - 13).attr("text-anchor", "middle").attr("class", "lab").style("font-size", narrow ? "10.5px" : "12px").text("Overall");
    rows.forEach((r, i) => {
      const y = top + i * cellH;
      svg.append("text").attr("x", r.key.startsWith("loo_") ? 12 : 0).attr("y", y + cellH / 2 + 4).attr("class", "lab").style("font-size", narrow ? "11px" : "12.5px")
        .style("fill", r.key.includes("v1") ? "var(--ink-3)" : "var(--ink)")
        .text(narrow ? r.arm.replace("Full audit, precision mode", "Precision mode").replace("v1: owner inferred (disclosed)", "v1 owner rule") : r.arm);
      defects.forEach((d, j) => {
        const [k, n] = r.cells[d], p = k / n, cx = labelW + j * cellW;
        svg.append("rect").attr("x", cx + 1).attr("y", y + 1).attr("width", cellW - 2).attr("height", cellH - 2).attr("rx", 3).style("fill", color(p));
        if (diag[r.key] === d) svg.append("rect").attr("x", cx + 2).attr("y", y + 2).attr("width", cellW - 4).attr("height", cellH - 4).attr("rx", 3).style("fill", "none").style("stroke", "var(--clk)").style("stroke-width", 2.2);
        svg.append("text").attr("x", cx + cellW / 2).attr("y", y + cellH / 2 + 4).attr("text-anchor", "middle").attr("class", "val").style("font-size", narrow ? "10px" : null).style("fill", p >= 0.6 ? "#ffffff" : "var(--ink)").text(`${k}/${n}`);
        svg.append("rect").attr("class", "hit").attr("x", cx).attr("y", y).attr("width", cellW).attr("height", cellH)
          .on("mousemove", (e) => showTip(e, `<b>${r.arm}</b><br>${names[d]}: <b>${k} of ${n}</b> correct verdicts` + (diag[r.key] === d ? `<br><span class="k">the defect this endpoint covers</span>` : ""))).on("mouseleave", hideTip);
      });
      svg.append("text").attr("x", W - accW / 2).attr("y", y + cellH / 2 + 4).attr("text-anchor", "middle").attr("class", "val").text(pct(r.acc));
      if (i === 2) svg.append("line").attr("x1", 0).attr("x2", W).attr("y1", y + cellH + 0.5).attr("y2", y + cellH + 0.5).style("stroke", "var(--ink-3)");
    });
  }

  /* ---------- Tables ---------- */
  function table(cols, rows) {
    return `<div class="tbl"><table><thead><tr>${cols.map((c) => `<th class="${c.n ? "n" : ""}">${c.h}</th>`).join("")}</tr></thead><tbody>` +
      rows.map((r) => `<tr>${cols.map((c) => `<td class="${c.n ? "n" : ""}">${c.f(r)}</td>`).join("")}</tr>`).join("") + `</tbody></table></div>`;
  }
  const ci = (r, m) => `${fmt(r[m])} <span style="color:var(--ink-3)">[${fmt(r[m + "_ci"][0])}, ${fmt(r[m + "_ci"][1])}]</span>`;
  const sw = (c) => `<span class="swatch" style="background:${c}"></span>`;
  const ARMCOLS = [
    { h: "Arm", f: (r) => sw(GROUP[r.group] || S.neutral) + r.arm }, { h: "BAcc [95% CI]", n: 1, f: (r) => ci(r, "bacc") },
    { h: "Recall [95% CI]", n: 1, f: (r) => ci(r, "recall") }, { h: "FPR [95% CI]", n: 1, f: (r) => ci(r, "fpr") },
    { h: "AUROC", n: 1, f: (r) => r.auroc }, { h: "n", n: 1, f: (r) => r.n },
    { h: "Median ms", n: 1, f: (r) => (r.median_ms ? Math.round(r.median_ms) : "—") }, { h: "Credits/row", n: 1, f: (r) => (r.credits ? fmt(r.credits) : r.group === "baseline" ? "0 (local)" : "—") },
  ];

  /* ---------- Figure builders ---------- */
  function rocSeries(curves) {
    return curves.map((c) => ({ name: c.arm, color: ARMCOLOR[c.arm] || S.neutral, dash: ARMDASH[c.arm], auroc: c.auroc, points: c.points.map((p) => ({ x: p.fpr, y: p.tpr, t: p.t })) }));
  }
  const rocTip = (s, p) => `<b>${s.name}</b> (AUROC ${fmt(s.auroc, 3)})<br>FPR <b>${pct(100 * p.x)}</b> · TPR <b>${pct(100 * p.y)}</b>` + (p.t != null ? `<br><span class="k">threshold ${fmt(p.t, 3)}</span>` : "");
  const OPS = {
    "Clocked default verdict": { color: S.clk, shape: "square", short: "default verdict" },
    "AgentAudit frozen (consensus)": { color: S.aa, shape: "circle", short: "frozen", fill: "var(--aa)" },
    "AgentAudit precision mode": { color: S.aa, shape: "diamond", short: "precision" },
  };
  function rocFigure(el, split, opt = {}) {
    const R = DATA.roc[split], series = rocSeries(R.curves);
    const labels = [], markers = [];
    Object.entries(R.operating_points).forEach(([k, p]) => {
      const o = OPS[k] || { color: S.neutral };
      markers.push({ x: p.fpr, y: p.tpr, color: o.color, shape: o.shape, fill: o.fill, text: opt.compact ? null : o.short,
        dx: 10, dy: o.short === "precision" ? 4 : o.short === "default verdict" ? 16 : 16,
        tip: `<b>${k}</b><br>FPR <b>${pct(100 * p.fpr)}</b> · recall <b>${pct(100 * p.tpr)}</b>` });
    });
    series.forEach((s) => (s.points = s.points.filter((p) => p.x <= 0.4 + 1e-9)));
    lines(el, series, { square: !!opt.square, height: opt.height || 300, xd: [0, 0.4], yd: [0, 1], diagonal: false, chance: true, title: opt.title,
      xl: "False-positive rate", yl: "True-positive rate", xf: (d) => Math.round(d * 100) + "%", yf: (d) => Math.round(d * 100) + "%", tip: rocTip, markers, labels, labelRoom: 16 });
    return series;
  }
  function legendHTML(items) {
    return items.map((i) => i.dash
      ? `<span><svg width="22" height="10" style="margin-right:6px;vertical-align:0"><line x1="0" y1="5" x2="22" y2="5" style="stroke:${i.color};stroke-width:2.2;stroke-dasharray:4 3"/></svg>${i.text}</span>`
      : `<span><i style="background:${i.color};${i.hollow ? "background:transparent;border:2px solid " + i.color : ""}"></i>${i.text}</span>`).join("");
  }

  const R = {
    hero() {
      const s = rocFigure(byId("h-roc"), "test", { title: "a  ROC, tool poisoning (held-out test)", height: 300, compact: false });
      byId("h-roc-legend").innerHTML = legendHTML(s.map((x) => ({ color: x.color, dash: x.dash, text: `${x.name} · AUROC ${fmt(x.auroc, 3)}` })));
      strips(byId("h-dist"), DATA.score_dist.test, { title: "b  Where each tool description lands", labelW: 128, bands: [
        { policy: "d", key: "p_default", y: 0, label: "Legitimate tools", sub: "Clocked default", color: "var(--clk)" },
        { policy: "d", key: "p_default", y: 1, label: "Attacks", sub: "Clocked default", color: "var(--clk)" },
        { policy: "a", key: "p_agentaudit", y: 0, label: "Legitimate tools", sub: "AgentAudit policy", color: "var(--aa)" },
        { policy: "a", key: "p_agentaudit", y: 1, label: "Attacks", sub: "AgentAudit policy", color: "var(--aa)" },
      ] });
      const F = DATA.forest, suites = ["Tool poisoning (test)", "Real-world tools (external)", "Scripts (test)", "Malicious skills (test)"];
      const pick = { "Tool poisoning (test)": ["Clocked Guard (default)", "Clocked + AgentAudit"], "Real-world tools (external)": ["Clocked Guard (default)", "Clocked + AgentAudit"],
        "Scripts (test)": ["Clocked Inspect (default)", "Clocked + AgentAudit"], "Malicious skills (test)": ["Clocked Inspect (default)", "AgentAudit pipeline"] };
      const rows = [];
      suites.forEach((su) => pick[su].forEach((arm) => {
        const f = F.find((r) => r.suite === su && r.arm === arm);
        rows.push({ label: `${su.replace(" (test)", "").replace(" (external)", "")} · ${f.group === "agentaudit" ? "AgentAudit" : "as shipped"}`, v: f.bacc, ci: f.bacc_ci, group: f.group,
          tip: `<b>${f.arm}</b><br>${su}<br>BAcc <b>${pct(f.bacc)}</b> <span class="k">[${fmt(f.bacc_ci[0])}, ${fmt(f.bacc_ci[1])}]</span>` });
      }));
      dots(byId("h-forest"), rows, { title: "c  Balanced accuracy, 95% CI", xd: [50, 100], unit: "%", labelW: 200 });
      byId("hero-table").innerHTML = table([{ h: "Suite", f: (r) => r.suite }, { h: "Arm", f: (r) => sw(GROUP[r.group]) + r.arm }, { h: "BAcc [95% CI]", n: 1, f: (r) => ci(r, "bacc") }, { h: "FPR", n: 1, f: (r) => fmt(r.fpr) }],
        F.filter((r) => pick[r.suite] && pick[r.suite].includes(r.arm)));
    },
    roc() {
      const s1 = rocFigure(byId("roc-test"), "test", { title: "Held-out test (n = 253)", height: 330 });
      rocFigure(byId("roc-ext"), "external", { title: "Never-seen real tools + published attacks (n = 249)", height: 330 });
      byId("roc-legend").innerHTML = legendHTML(s1.map((x) => ({ color: x.color, dash: x.dash, text: `${x.name}` }))) +
        `<span>□ default verdict rule</span><span>● frozen AgentAudit</span><span>◇ precision mode</span>`;
      byId("roc-table").innerHTML = ["test", "external"].map((sp) => `<p class="fig-title" style="margin:10px 0 0">${sp}</p>` +
        table([{ h: "Curve", f: (r) => r.arm }, { h: "AUROC", n: 1, f: (r) => fmt(r.auroc, 3) }], DATA.roc[sp].curves) +
        table([{ h: "Operating point", f: (r) => r[0] }, { h: "FPR", n: 1, f: (r) => pct(100 * r[1].fpr) }, { h: "TPR", n: 1, f: (r) => pct(100 * r[1].tpr) }], Object.entries(DATA.roc[sp].operating_points))).join("");
    },
    dist() {
      const rows = DATA.score_dist.test;
      const src = { mcp_reference: "Reference MCP servers", injecagent: "InjecAgent tool specs", hard_negative: "Hard negatives", mcptox: "MCPTox attacks" };
      const bands = [];
      ["p_default", "p_agentaudit"].forEach((key) => Object.keys(src).forEach((s) => bands.push({ policy: key, key, y: s, attack: s === "mcptox", src: s,
        label: src[s], sub: key === "p_default" ? "Clocked default" : "AgentAudit policy", color: key === "p_default" ? "var(--clk)" : "var(--aa)" })));
      const W = byId("dist");
      const rows2 = rows.map((r) => Object.assign({}, r, { label: r.source }));
      strips(W, rows2, { title: "Guard probability by source, held-out test (n = 253)", labelW: 170, bands: bands.map((b) => Object.assign({}, b, { y: b.src })) });
      byId("dist-table").innerHTML = table([{ h: "Source", f: (r) => src[r[0]] }, { h: "n", n: 1, f: (r) => r[1].n },
        { h: "≥ 0.5, default", n: 1, f: (r) => r[1].d }, { h: "≥ 0.5, AgentAudit", n: 1, f: (r) => r[1].a }],
        Object.keys(src).map((s) => { const p = rows.filter((r) => r.source === s); return [s, { n: p.length, d: p.filter((r) => r.p_default >= 0.5).length, a: p.filter((r) => r.p_agentaudit >= 0.5).length }]; }));
    },
    sweep() {
      const T = DATA.threshold_sweep, arms = Object.keys(T);
      const mk = (metric) => arms.map((a) => ({ name: a, color: ARMCOLOR[a] || S.neutral, points: T[a].map((p) => ({ x: p.t, y: p[metric], p })) }));
      const tipf = (metric) => (s, p) => `<b>${s.name}</b><br>threshold ${fmt(p.x, 2)}<br>BAcc <b>${pct(p.p.bacc)}</b> · FPR <b>${pct(p.p.fpr)}</b> · recall <b>${pct(p.p.recall)}</b>`;
      lines(byId("sw-bacc"), mk("bacc"), { height: 250, xd: [0, 1], yd: [50, 100], title: "Balanced accuracy vs threshold", xl: "Threshold on injection probability", yl: "%", tip: tipf("bacc"), vline: 0.5, vlabel: "0.5" });
      lines(byId("sw-fpr"), mk("fpr"), { height: 250, xd: [0, 1], yd: [0, 80], title: "False-positive rate vs threshold", xl: "Threshold on injection probability", yl: "%", tip: tipf("fpr"), vline: 0.5, vlabel: "0.5" });
      byId("sw-legend").innerHTML = legendHTML(arms.map((a) => ({ color: ARMCOLOR[a], text: a })));
      byId("sw-table").innerHTML = table([{ h: "Threshold", f: (r) => fmt(r.t, 2) }].concat(arms.flatMap((a) => [{ h: a + " BAcc", n: 1, f: (r) => fmt((T[a].find((p) => p.t === r.t) || {}).bacc) }, { h: "FPR", n: 1, f: (r) => fmt((T[a].find((p) => p.t === r.t) || {}).fpr) }])),
        T[arms[0]].filter((_, i) => i % 4 === 0));
    },
    calib() {
      const C = DATA.calibration, arms = Object.keys(C);
      const series = arms.map((a) => ({ name: a, color: ARMCOLOR[a] || S.neutral, dots: true, thin: true, ece: C[a].ece,
        points: C[a].bins.map((b) => ({ x: b.mean_p, y: b.frac_pos, n: b.n, r: Math.max(3, Math.min(9, Math.sqrt(b.n) * 0.9)) })) }));
      lines(byId("calib"), series, { height: 300, xd: [0, 1], yd: [0, 1], diagonal: true, title: "Reliability diagram (held-out test)", xl: "Mean predicted probability", yl: "Observed share of attacks",
        tip: (s, p) => `<b>${s.name}</b> (ECE ${fmt(s.ece, 3)})<br>predicted ${fmt(p.x, 2)} · observed ${fmt(p.y, 2)}<br><span class="k">${p.n} rows in this bin</span>` });
      byId("calib-legend").innerHTML = legendHTML(series.map((s) => ({ color: s.color, text: `${s.name} · ECE ${fmt(s.ece, 3)}` }))) + `<span>dot area ∝ rows per bin; dashed = perfect calibration</span>`;
      byId("calib-table").innerHTML = arms.map((a) => `<p class="fig-title" style="margin:10px 0 0">${a} · ECE ${fmt(C[a].ece, 3)}</p>` +
        table([{ h: "Bin from", f: (b) => fmt(b.lo, 1) }, { h: "Mean p", n: 1, f: (b) => fmt(b.mean_p, 3) }, { h: "Observed", n: 1, f: (b) => fmt(b.frac_pos, 3) }, { h: "n", n: 1, f: (b) => b.n }], C[a].bins)).join("");
    },
    bysrc() {
      const names = { mcp_reference: "Reference MCP servers (test)", injecagent: "InjecAgent tool specs (test)", hard_negative: "Hard negatives (test)", registry_real: "199 real public tools (never seen)" };
      const rows = [];
      Object.keys(names).forEach((s) => DATA.by_source.filter((r) => r.source === s).forEach((r) => rows.push({
        label: names[s] + (r.arm.includes("AgentAudit") ? " · AgentAudit" : " · as shipped"), v: r.fpr, ci: r.ci, group: r.arm.includes("AgentAudit") ? "agentaudit" : "clocked",
        tip: `<b>${names[s]}</b><br>${r.arm}: <b>${r.flagged} of ${r.n}</b> flagged (${pct(r.fpr)})<br><span class="k">95% Wilson CI [${fmt(r.ci[0])}, ${fmt(r.ci[1])}]</span>` })));
      dots(byId("bysrc"), rows, { title: "Legitimate tool descriptions wrongly flagged, by source", xd: [0, 70], unit: "%", labelW: 290 });
      byId("bysrc-table").innerHTML = table([{ h: "Split", f: (r) => r.split }, { h: "Source", f: (r) => r.source }, { h: "Arm", f: (r) => r.arm }, { h: "Flagged", n: 1, f: (r) => `${r.flagged}/${r.n}` }, { h: "FPR [95% CI]", n: 1, f: (r) => `${fmt(r.fpr)} [${fmt(r.ci[0])}, ${fmt(r.ci[1])}]` }],
        DATA.by_source.filter((r) => r.source !== "mtp_pair"));
    },
    ablation() {
      const a = DATA.ablation, v = (i, m) => a[i][m];
      const st = (m) => [
        { label: "Clocked as shipped", from: 0, to: v(0, m), color: "var(--clk)" },
        { label: "+ agent-specific policy", from: v(0, m), to: v(2, m), color: "var(--aa)" },
        { label: "+ consensus rule", from: v(2, m), to: v(3, m), color: "var(--aa)" },
        { label: "Clocked + AgentAudit", from: 0, to: v(3, m), color: "var(--aa)" }];
      steps(byId("abl-bacc"), st("bacc"), { title: "Balanced accuracy", max: 100, metricName: "Balanced accuracy" });
      steps(byId("abl-fpr"), st("fpr"), { title: "False-positive rate", max: 30, metricName: "False-positive rate" });
      byId("abl-table").innerHTML = table(ARMCOLS.slice(0, 6), a.map((r) => Object.assign({}, r, { group: r.arm.startsWith("AgentAudit") ? "agentaudit" : "clocked" })));
    },
    forest() {
      const F = DATA.forest, suites = ["Tool poisoning (test)", "Real-world tools (external)", "Scripts (test)", "Malicious skills (test)"];
      const rows = [];
      suites.forEach((su) => {
        rows.push({ header: su });
        F.filter((r) => r.suite === su).forEach((r) => rows.push({ label: r.arm, v: r.bacc, ci: r.bacc_ci, group: r.group, hollow: r.arm.includes("tuned"),
          tip: `<b>${r.arm}</b><br>${su}<br>BAcc <b>${pct(r.bacc)}</b> <span class="k">[${fmt(r.bacc_ci[0])}, ${fmt(r.bacc_ci[1])}]</span><br>FPR ${pct(r.fpr)}` + (r.credits ? ` · ${fmt(r.credits)} credits/row` : " · local") }));
      });
      dots(byId("forest"), rows, { title: "", xd: [50, 100], unit: "%", labelW: 240, xl: "Balanced accuracy, 95% bootstrap CI", ref: 50, refLabel: "" });
      byId("forest-table").innerHTML = table([{ h: "Suite", f: (r) => r.suite }, { h: "Arm", f: (r) => sw(GROUP[r.group]) + r.arm }, { h: "BAcc [95% CI]", n: 1, f: (r) => ci(r, "bacc") }, { h: "FPR", n: 1, f: (r) => fmt(r.fpr) }, { h: "Credits/row", n: 1, f: (r) => (r.credits ? fmt(r.credits) : "0 (local)") }], F);
    },
    scope() {
      const rows = DATA.inspect.scope_pairs.map((r) => ({ label: r.arm, v: r.bacc, ci: r.bacc_ci, group: r.group, tip: `<b>${r.arm}</b><br>accuracy <b>${pct(r.bacc)}</b> <span class="k">[${fmt(r.bacc_ci[0])}, ${fmt(r.bacc_ci[1])}]</span><br>n = ${r.n} rows (14 pairs)` }));
      dots(byId("scope"), rows, { title: "Accuracy on scope pairs (14 held-out pairs)", xd: [0, 100], unit: "%", labelW: 240, ref: 50, refLabel: "chance" });
      byId("scope-table").innerHTML = table(ARMCOLS.slice(0, 6), DATA.inspect.scope_pairs) + table(ARMCOLS, DATA.inspect.all);
    },
    skills() {
      const series = DATA.skills_roc.map((c) => ({ name: c.arm, auroc: c.auroc, color: ARMCOLOR[c.arm] || S.neutral, dash: ARMDASH[c.arm], points: c.points.map((p) => ({ x: p.fpr, y: p.tpr, t: p.t })) }));
      const op = (name) => DATA.skills.find((r) => r.arm === name);
      const markers = [["AgentAudit pipeline", S.aa, "circle", "var(--aa)"], ["Clocked Inspect (default)", S.clk, "square"], ["Supply-chain check only", S.aa, "diamond"]].map(([n, c, sh, f]) => {
        const r = op(n);
        return { x: r.fpr / 100, y: r.recall / 100, color: c, shape: sh, fill: f, tip: `<b>${n}</b> at its frozen rule<br>FPR <b>${pct(r.fpr)}</b> · recall <b>${pct(r.recall)}</b>` };
      });
      series.forEach((s) => (s.points = s.points.filter((p) => p.x <= 0.4 + 1e-9)));
      lines(byId("sk-roc"), series, { height: 320, xd: [0, 0.4], yd: [0, 1], chance: true, title: "ROC, malicious skills (held-out test, n = 244)", xl: "False-positive rate", yl: "True-positive rate",
        xf: (d) => Math.round(d * 100) + "%", yf: (d) => Math.round(d * 100) + "%", tip: rocTip, markers });
      byId("sk-legend").innerHTML = legendHTML(series.map((s) => ({ color: s.color, dash: s.dash, text: `${s.name} · AUROC ${fmt(s.auroc, 3)}` }))) + `<span>markers: each arm's frozen operating point</span>`;
      const rows = DATA.skills.map((r) => ({ label: r.arm, v: r.recall, ci: r.recall_ci, group: r.group, tip: `<b>${r.arm}</b><br>recall <b>${pct(r.recall)}</b> · FPR <b>${pct(r.fpr)}</b>` }));
      dots(byId("sk-rec"), rows, { title: "Recall at the frozen rule, 95% CI", xd: [0, 100], unit: "%", labelW: 190 });
      byId("sk-table").innerHTML = table(ARMCOLS, DATA.skills);
    },
    governance() {
      heatmap(byId("gov"));
      const G = DATA.governance;
      byId("gov-table").innerHTML = table([{ h: "Arm", f: (r) => r.arm }, { h: "Accuracy", n: 1, f: (r) => pct(r.acc) }].concat(G.defects.map((d) => ({ h: d.replace("_", " "), n: 1, f: (r) => r.cells[d].join("/") }))), G.rows);
    },
    precision() {
      const P = DATA.precision_curve;
      const series = [
        { name: "Recall", color: S.aa, points: P.map((p) => ({ x: p.t, y: p.recall, p })) },
        { name: "Balanced accuracy", color: S.aa, dash: "5 4", points: P.map((p) => ({ x: p.t, y: p.bacc, p })) },
        { name: "False-positive rate", color: S.clk, points: P.map((p) => ({ x: p.t, y: p.fpr, p })) },
      ];
      const at = P.find((p) => p.t === 0.3);
      lines(byId("prec"), series, { height: 280, xd: [0, 1], yd: [0, 100], title: "Guard test (n = 253): adjudication threshold sweep", xl: "Decide second-opinion threshold (0 = no adjudication)", yl: "%",
        tip: (s, p) => `<b>threshold ${fmt(p.x, 2)}</b><br>recall ${pct(p.p.recall)} · FPR ${pct(p.p.fpr)} · BAcc ${pct(p.p.bacc)}`, vline: 0.3, vlabel: "chosen on dev: 0.3",
        labels: [{ x: 0.97, y: P[P.length - 1].recall, text: "recall", anchor: "end", dy: -8, dx: 0 }, { x: 0.97, y: P[P.length - 1].bacc, text: "balanced accuracy", anchor: "end", dy: -14, dx: 0 }, { x: 0.97, y: 2, text: "false-positive rate", anchor: "end", dy: -6, dx: 0 }],
        markers: [{ x: 0.3, y: at.recall, color: S.aa, shape: "diamond", tip: `<b>precision mode (t = 0.3)</b><br>recall ${pct(at.recall)} · FPR ${pct(at.fpr)}` }, { x: 0, y: P[0].recall, color: S.aa, shape: "circle", fill: "var(--aa)", tip: `<b>default mode (no adjudication)</b><br>recall ${pct(P[0].recall)} · FPR ${pct(P[0].fpr)}` }] });
      const g = (k, a) => DATA[k].find((r) => r.arm === a);
      byId("prec-cards").innerHTML = [["Never-seen data", "guard_external"], ["Held-out test", "guard_test"]].map(([nm, k]) => {
        const d = g(k, "Clocked + AgentAudit"), p = g(k, "AgentAudit, precision mode");
        return `<div class="stat"><div class="k">${nm}</div><div class="row"><span>default</span><b>${pct(d.recall)}</b> recall · <b>${pct(d.fpr)}</b> FPR</div><div class="row"><span>precision</span><b>${pct(p.recall)}</b> recall · <b>${pct(p.fpr)}</b> FPR</div></div>`;
      }).join("") + `<div class="stat"><div class="k">Real-world, 9 public servers</div><div class="row"><span>default</span><b>2 / 9</b> wrongly quarantined</div><div class="row"><span>precision</span><b>0 / 9</b> wrongly quarantined</div></div>`;
      byId("prec-table").innerHTML = table([{ h: "Threshold", f: (r) => fmt(r.t, 2) }, { h: "Recall", n: 1, f: (r) => fmt(r.recall) }, { h: "FPR", n: 1, f: (r) => fmt(r.fpr, 2) }, { h: "BAcc", n: 1, f: (r) => fmt(r.bacc) }], P);
    },
    costfig() {
      cost(byId("cost"));
      latency(byId("lat"));
      byId("cost-table").innerHTML = table([{ h: "Suite", f: (r) => r.suite }, { h: "Arm", f: (r) => r.arm }, { h: "BAcc", n: 1, f: (r) => fmt(r.bacc) }, { h: "Credits/row", n: 1, f: (r) => (r.credits ? fmt(r.credits) : "0 (local)") }, { h: "Median ms", n: 1, f: (r) => (r.median_ms ? Math.round(r.median_ms) : "—") }], DATA.forest) +
        table([{ h: "Endpoint", f: (r) => r.endpoint }, { h: "n", n: 1, f: (r) => r.n }, { h: "p10", n: 1, f: (r) => r.p10 }, { h: "p50", n: 1, f: (r) => r.p50 }, { h: "p90", n: 1, f: (r) => r.p90 }], DATA.latency);
    },
    jev() {
      const rows = DATA.jev, names = { route: "Route", triage: "Triage", score: "Size", gate: "Risk" }, el = byId("jev"), W = width(el), labelW = 90, rowH = 34, H = 10 + rows.length * rowH + 30;
      const svg = frame(el, W, H, "jev-benchmark reproduction");
      const x = d3.scaleLinear().domain([0, 100]).range([labelW, W - 120]);
      svg.append("g").attr("class", "grid").selectAll("line").data(x.ticks(5)).join("line").attr("x1", (d) => x(d)).attr("x2", (d) => x(d)).attr("y1", 10).attr("y2", H - 26);
      svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - 26})`).call(d3.axisBottom(x).ticks(5).tickSize(4).tickFormat((d) => d + "%"));
      rows.forEach((r, i) => {
        const cy = 10 + i * rowH + rowH / 2;
        svg.append("text").attr("class", "lab").attr("x", labelW - 12).attr("y", cy + 4).attr("text-anchor", "end").text(names[r.task] || r.task);
        svg.append("rect").attr("x", x(r.jev) - 5).attr("y", cy - 5).attr("width", 10).attr("height", 10).attr("rx", 2).style("fill", "var(--neutral)");
        svg.append("circle").attr("cx", x(r.published)).attr("cy", cy).attr("r", 9).style("fill", "none").style("stroke", "var(--ink-2)").style("stroke-width", 2);
        svg.append("circle").attr("cx", x(r.ours)).attr("cy", cy).attr("r", 5).style("fill", "var(--clk)");
        svg.append("text").attr("class", "val").attr("x", W - 112).attr("y", cy + 4).text(`${fmt(r.ours)} = ${fmt(r.published)}`);
        svg.append("rect").attr("class", "hit").attr("x", 0).attr("y", cy - rowH / 2).attr("width", W).attr("height", rowH)
          .on("mousemove", (e) => showTip(e, `<b>${names[r.task]}</b> (n = ${r.n})<br>Clocked, our run: <b>${pct(r.ours)}</b><br>Clocked, published: <b>${pct(r.published)}</b><br>Jev 1.13, published: <b>${pct(r.jev)}</b>`)).on("mouseleave", hideTip);
      });
      byId("jev-table").innerHTML = table([{ h: "Task", f: (r) => r.task }, { h: "n", n: 1, f: (r) => r.n }, { h: "Clocked, our run", n: 1, f: (r) => fmt(r.ours) }, { h: "Clocked, published", n: 1, f: (r) => fmt(r.published) }, { h: "Jev 1.13, published", n: 1, f: (r) => fmt(r.jev) }], rows);
    },
  };

  function renderAll() {
    Object.keys(R).forEach((k) => { try { R[k](); } catch (e) { console.error("figure " + k, e); } });
  }

  /* ---------- Appendix ---------- */
  function appendix() {
    const blocks = [["Tool poisoning, held-out test (n = 253)", DATA.guard_test], ["Never-seen data (n = 249)", DATA.guard_external],
      ["Scripts, held-out test (n = 206)", DATA.inspect.all], ["Scripts without scope pairs (n = 178)", DATA.inspect.no_scope_pairs], ["Malicious skills, held-out test (n = 244)", DATA.skills]];
    byId("appendix-tables").innerHTML = blocks.map(([t, rows]) => `<p class="fig-title" style="margin:22px 0 0">${t}</p>` + table(ARMCOLS, rows)).join("");
    const d = DATA.determinism;
    byId("det").textContent = `${d.same_verdict}/${d.n} verdicts, ${d.same_category}/${d.n} categories, maximum probability change ${d.max_abs_dp}`;
  }

  /* ---------- Worked examples ---------- */
  const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  function highlighted(text, hs) {
    let out = "", pos = 0;
    hs.slice().sort((a, b) => a.start - b.start).forEach((h) => {
      if (h.start < pos) return;
      out += esc(text.slice(pos, h.start)) + `<mark class="${h.check.split(" ")[0]}" title="${esc(h.check + ": " + h.label)}">${esc(text.slice(h.start, h.end))}</mark>`;
      pos = h.end;
    });
    return out + esc(text.slice(pos));
  }
  function exampleHTML(e) {
    const vClass = e.verdict === "quarantine" ? "q" : e.verdict === "approve" ? "ok" : "rv";
    const arts = e.artifacts.map((a) => `<div class="artifact"><div class="a-head">${esc(a.label)}</div><pre>${highlighted(a.text, a.highlights)}</pre></div>`).join("");
    const finds = [];
    e.artifacts.forEach((a) => {
      // One row per distinct finding; several highlighted spans of the same finding collapse into a count.
      const counts = new Map();
      a.highlights.forEach((h) => { const k = h.check + "\u0000" + h.label; counts.set(k, { h, n: (counts.get(k)?.n || 0) + 1 }); });
      counts.forEach(({ h, n }) => finds.push(`<li><span class="pill">${esc(h.check)}</span>${esc(h.label)}${n > 1 ? ` · ${n} spans` : ""}<br><span style="color:var(--ink-3);font-size:12px">${esc(a.label)}</span></li>`));
    });
    let extra = "";
    if (e.tools) extra = `<div class="verdict"><b style="font-size:13px">Per-tool recommendation</b><table class="tooltable"><thead><tr><th>Tool</th><th>Now</th><th>Recommendation</th></tr></thead><tbody>` +
      e.tools.map((t) => `<tr><td class="mono">${esc(t.tool)}</td><td>${t.enabled ? "on" : "off"}</td><td><span class="pill ${t.rec === "keep_disabled" ? "q" : t.rec === "enable" ? "ok" : "rv"}">${t.rec}</span></td></tr>`).join("") +
      `</tbody></table><p style="font-size:12px;color:var(--ink-3);margin:8px 0 0">${esc(e.source_note || "")}</p></div>`;
    if (e.duplicate) extra = `<div class="verdict"><b style="font-size:13px">Registry check</b><ul class="findings-list"><li><span class="pill">Compare</span>overlaps <span class="mono">${esc(e.duplicate.of)}</span>, related = ${e.duplicate.related.toFixed(3)}</li>` +
      e.duplicate.rerank.map((r) => `<li><span class="pill">Rerank</span><span class="mono">${esc(r.agent)}</span>: ${r.action} (score ${r.score.toFixed(3)})</li>`).join("") + `</ul></div>`;
    return `<div class="ex-grid"><div><p class="ex-title">${esc(e.title)}</p><p class="ex-agent">${esc(e.agent)}</p>${arts}</div>
      <div class="side"><div class="verdict"><div style="font-size:12px;color:var(--ink-3)">Verdict</div><div class="v"><span class="pill ${vClass}">${e.verdict}</span> ${Math.round(e.confidence * 100)}% confidence</div>
      <p style="font-size:14px;margin:10px 0 0">${esc(e.summary)}</p><div style="margin-top:8px">${e.endpoints.map((x) => `<span class="pill">${x}</span>`).join("")}</div></div>
      ${finds.length ? `<div class="verdict"><b style="font-size:13px">Evidence</b><ul class="findings-list">${finds.join("")}</ul></div>` : ""}${extra}</div></div>`;
  }
  function examples() {
    const tabs = byId("ex-tabs"), body = byId("ex-body");
    EX.forEach((e, i) => {
      const b = document.createElement("button");
      b.setAttribute("role", "tab");
      b.setAttribute("aria-selected", i === 0 ? "true" : "false");
      b.textContent = e.tab;
      b.addEventListener("click", () => {
        tabs.querySelectorAll("button").forEach((x) => x.setAttribute("aria-selected", "false"));
        b.setAttribute("aria-selected", "true");
        body.innerHTML = exampleHTML(e);
      });
      tabs.appendChild(b);
    });
    body.innerHTML = exampleHTML(EX[0]);
  }

  /* ---------- Controls ---------- */
  document.querySelectorAll("[data-table]").forEach((btn) => btn.addEventListener("click", () => {
    const on = byId(btn.dataset.table).classList.toggle("show-table");
    btn.textContent = on ? "Chart view" : "Table view";
  }));
  const copy = byId("copy-cite");
  copy.addEventListener("click", () => {
    const t = byId("cite-text").textContent;
    const done = () => { copy.textContent = "Copied"; setTimeout(() => (copy.textContent = "Copy citation"), 1600); };
    try { navigator.clipboard.writeText(t).then(done, () => (copy.textContent = "Select and copy")); } catch (e) { copy.textContent = "Select and copy"; }
  });

  examples();
  appendix();
  renderAll();
  let rt;
  window.addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(renderAll, 150); });
  new MutationObserver(renderAll).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
})();
