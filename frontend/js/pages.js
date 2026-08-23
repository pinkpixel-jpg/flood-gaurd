/* FloodGuard — page data binding (real FastAPI data only).
   Preserves the existing UI: we fill existing containers, never redesign.
   Loading / offline / empty states shown when backend unavailable.
   Nothing is invented client-side. */

(function () {
  /* visible diagnostics: any uncaught error/rejection shows on-screen so
     demo failures are never silent. Remove before final production. */
  function fgShowError(msg) {
    var el = document.getElementById("fg-debug-error");
    if (!el) {
      el = document.createElement("div");
      el.id = "fg-debug-error";
      el.style.cssText =
        "position:fixed;bottom:0;left:0;right:0;z-index:99999;" +
        "background:#7b241c;color:#fff;font:12px/1.5 'IBM Plex Mono',monospace;" +
        "padding:10px 14px;max-height:38vh;overflow:auto";
      (document.body || document.documentElement).appendChild(el);
    }
    var line = document.createElement("div");
    line.textContent = "⚠ " + msg;
    el.appendChild(line);
    console.error("[FloodGuard debug]", msg);
  }
  window.addEventListener("error", function (e) {
    fgShowError(e.message + "  @" + (e.filename || "") + ":" + e.lineno);
  });
  window.addEventListener("unhandledrejection", function (e) {
    fgShowError("Unhandled promise rejection: " + e.reason);
  });
  window.fgShowError = fgShowError;

  const state = { date: "2024-07-15", grid: "PUNE_G004" };
  let GRIDS = (window.FG_DATASET && window.FG_DATASET.FALLBACK_GRIDS.slice()) ||
              ["PUNE_G001", "PUNE_G002", "PUNE_G003", "PUNE_G004"];
  const DATE_MIN = (window.FG_DATASET && window.FG_DATASET.DATE_MIN) || "2015-01-01";
  const DATE_MAX = (window.FG_DATASET && window.FG_DATASET.DATE_MAX) || "2025-12-31";

  async function ensureGrids() {
    if (window.loadGrids) GRIDS = await window.loadGrids();
    return GRIDS;
  }

  function buildDateInput(id) {
    const inp = document.createElement("input");
    inp.type = "date"; inp.id = id;
    inp.min = DATE_MIN;
    inp.max = (window.FG_DATASET && FG_DATASET.DATE_MAX) || "2026-03-31";
    inp.value = state.date;
    inp.style.cssText = "background:#22303A;color:var(--ink,#fff);padding:12px 16px;border-radius:999px;border:1px solid var(--line)";
    inp.setAttribute("aria-label", "Date selection");
    return inp;
  }

  function buildZoneSelect(existingSel) {
    const sel = existingSel || document.createElement("select");
    sel.innerHTML = "";
    GRIDS.forEach(g => {
      const o = document.createElement("option");
      o.value = g;
      o.textContent = (window.zoneName ? zoneName(g) : g);
      sel.appendChild(o);
    });
    sel.value = state.grid;
    return sel;
  }

  const qs = (sel) => document.querySelector(sel);
  const esc = (s) => String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  function loading(el, msg) {
    if (el) el.innerHTML = '<p class="form-note">Loading ' + (msg || "data") + '…</p>';
  }
  function offline(el) {
    if (el) el.innerHTML =
      '<p class="form-note" style="color:#e07a5f">Unable to connect to FloodGuard backend.</p>';
  }
  function empty(el, msg) {
    if (el) el.innerHTML = '<p class="form-note">' + (msg || "No data available.") + '</p>';
  }
  function levelDot(level) {
    if (level === "LOW") return "risk-low";
    if (level === "MODERATE" || level === "HIGH") return "risk-med";
    return "risk-high";
  }
  function replayBadge(mode) {
    if (mode === "PREDICTION") {
      return '<span class="fg-badge-replay" style="background:#e67e22">FORECAST / PREDICTION — experimental, not measured data</span>';
    }
    return "";
  }

  async function fetchZones() {
    try { return await FGApi.getZones(state.date); }
    catch (e) { return null; }
  }

  /* ---------- HOME ---------- */
  async function pageIndex() {
    const grid = qs(".stats-grid");
    if (!grid) return;
    loading(grid, "zone status");
    const zones = await fetchZones();
    if (!zones) return offline(grid);
    const list = Array.isArray(zones) ? zones : zones.zones;
    if (!list || !list.length) return empty(grid);

    const scores = list.map(z => z.risk.score);
    const avg = (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1);
    const high = list.filter(z => z.risk.level === "HIGH").length;
    const crit = list.filter(z => z.risk.level === "CRITICAL").length;
    const top = list.reduce((a, b) =>
      (b.risk ? b.risk.score : 0) > (a.risk ? a.risk.score : 0) ? b : a);
    const date = top.date || state.date;

    const cards = [
      stat(String(list.length), "", "Total zones", "IMD grid cells"),
      stat(String(high), "", "High-risk zones", "level HIGH"),
      stat(String(crit), "", "Critical-risk zones", "level CRITICAL"),
      stat(String(avg), "", "Average zone risk", "current replay date"),
      stat(String(high + crit), "", "Active alerts", "HIGH + CRITICAL zones"),
      stat(date, "", "Analysis date", "current date")
    ];
    grid.innerHTML = cards.join("");
  }
  function stat(num, suffix, label, src) {
    return '<div class="stat"><div class="stat-num"><span>' + esc(num) +
      "</span>" + (suffix ? "<em>" + esc(suffix) + "</em>" : "") +
      '</div><div class="stat-label mono">' + esc(label) +
      '</div><div class="stat-src mono">' + esc(src) + "</div></div>";
  }

  /* ---------- LIVE MAP ---------- */
  const ZONE_SHORT = {};

  async function pageLiveMap() {
    await ensureGrids();
    const feed = document.getElementById("feedList");
    const gaugePanel = qs(".gauge-list");
    loading(feed, "zone risk feed");
    if (gaugePanel) loading(gaugePanel, "river gauge telemetry");

    const zones = await fetchZones();
    if (!zones) { offline(feed); if (gaugePanel) offline(gaugePanel); return; }
    const list = Array.isArray(zones) ? zones : zones.zones;
    if (!list || !list.length) { empty(feed); return; }

    // short place names for map labels
    list.forEach(z => {
      ZONE_SHORT[z.grid_id] = window.zoneShort
        ? zoneShort(z.grid_id)
        : String(z.zone_name || z.grid_id).replace(/\s*Pune\s*$/i, "");
    });

    /* ---- structured sensor/risk feed ---- */
    if (feed) {
      feed.innerHTML = list.map(z => {
        const lvlClass = z.risk.level === "CRITICAL" ? "lvl-risk"
                       : z.risk.level === "HIGH" ? "lvl-warn" : "";
        return '<div class="feed-row" style="display:block">' +
          '<div style="display:flex;justify-content:space-between;gap:8px">' +
          '<b>' + esc(ZONE_SHORT[z.grid_id]) + '</b>' +
          '<span class="' + lvlClass + '" style="font-weight:700">' +
          esc(z.risk.level) + '</span></div>' +
          '<div style="opacity:.85">score ' + esc(Number(z.risk.score).toFixed(2)) +
          ' · trend ' + esc(z.risk.trend || "n/a") +
          ' · vuln ' + esc(Number(z.vulnerability.score).toFixed(1)) +
          '</div><div class="feed-time mono">' + esc(z.date) +
          '</div></div>';
      }).join("") +
      '<p class="form-note">No live sensor mesh is connected. Rows above are ' +
      'backend risk results for the replay date - nothing is simulated.</p>';
    }

    /* ---- river gauge telemetry (REAL CWC values) ---- */
    if (gaugePanel) {
      gaugePanel.innerHTML = list.map(z => {
        const rv = z.river || {};
        const ok = rv.available;
        return '<div class="gauge' + (ok ? '' : '') + '">' +
          '<span class="gauge-name">' + esc(ZONE_SHORT[z.grid_id] || z.grid_id) +
          ' - river level</span>' +
          '<span class="gauge-val status-chip">' +
          (ok ? Number(rv.level_max_m).toFixed(2) + ' m' : 'UNAVAILABLE') +
          '</span>' +
          '<div class="gauge-sub"><span class="form-note">' +
          (ok ? 'mean ' + Number(rv.level_mean_m).toFixed(2) + ' m · ' +
                rv.stations + ' CWC station(s) · ' + esc(z.date)
             : 'No CWC station for this cell/date') +
          '</span></div></div>';
      }).join("") +
      '<p class="form-note">Values are REAL CWC telemetry readings. G002 has ' +
      'no station, and older dates predate telemetry - shown as UNAVAILABLE, ' +
      'never estimated.</p>';
    }

    /* ---- bind dots: bigger hit area, place-name labels, click ---- */
    const groups = document.querySelectorAll(".map-zone");
    GRIDS.forEach(gid => {
      const g = document.querySelector(
        '.map-zone[data-grid="' + gid + '"]');
      const z = list.find(x => x.grid_id === gid);
      if (!g || !z) return;
      g.classList.remove("risk-low", "risk-med", "risk-high");
      g.classList.add(levelDot(z.risk.level));
      g.setAttribute("data-grid", gid);
      g.style.cursor = "pointer";
      g.querySelectorAll("circle").forEach(c => {
        c.setAttribute("r", c.classList.contains("halo") ? 24 : 11);
      });
      g.addEventListener("click", () => renderMapDetail(gid));
      const t = document.createElementNS("http://www.w3.org/2000/svg", "title");
      t.textContent = ZONE_SHORT[gid] + " (" + gid + ") - " + z.risk.level +
                      " " + z.risk.score + "/100 - click for details";
      g.appendChild(t);
    });

    // delegated safety-net: any click on a dot (even re-rendered ones)
    qs(".map-board").addEventListener("click", function (e) {
      const g = e.target.closest(".map-zone");
      if (g && g.dataset.grid) renderMapDetail(g.dataset.grid);
    });

    /* default: preselect the highest-risk zone so the panel is never empty */
    const top = list.reduce((a, b) =>
      b.risk.score > a.risk.score ? b : a);
    await renderMapDetail(top.grid_id);
  }

  async function renderMapDetail(gid) {
    const box = document.getElementById("fg-map-detail");
    if (!box) return;
    loading(box, "zone details");

    let z, prev, env;
    try {
      z = await FGApi.getZone(gid, state.date);
      prev = await FGApi.getPrevention(gid, state.date,
                                       (z.citizen_reports || {}).count || 0);
      prev = prev.prevention || prev;
      const envResp = await FGApi.getEnvironment(gid, state.date);
      env = envResp.environment || envResp;
    } catch (e) { return offline(box); }

    const factors = (z.vulnerability.explanations || []);
    box.innerHTML =
      '<div class="panel-head"><h3>' +
      esc(window.zoneName ? zoneName(gid) : (ZONE_SHORT[gid] || gid)) +
      '</h3></div>' +

      '<div style="padding:0 20px 16px">' +

        '<h4>Risk</h4>' +
        '<div class="fg-kv"><span>Score</span><b>' + esc(z.risk.score) + ' / 100</b></div>' +
        '<div class="fg-kv"><span>Level</span><b style="color:' +
          levelColor(z.risk.level) + '">' + esc(z.risk.level) + '</b></div>' +
        '<div class="fg-kv"><span>Trend</span><b>' + esc(z.risk.trend || 'n/a') + '</b></div>' +
        '<div class="fg-kv"><span>Date</span><b>' + esc(z.date) + '</b></div>' +

        '<h4>Vulnerability</h4>' +
        '<div class="fg-kv"><span>Score</span><b>' +
          esc(z.vulnerability.score) + ' / 100 — ' + esc(z.vulnerability.level) + '</b></div>' +
        (factors.length
          ? '<ul class="check-list">' + factors.map(f =>
              '<li class="check-item">' +
              '<span class="check-mark">→</span>' +
              '<span class="check-txt">' + esc(f) + '</span></li>').join('') +
            '</ul>'
          : '') +

        '<h4>Environment</h4>' +
        '<div class="fg-kv"><span>Heat exposure</span><b>' +
          (env.heat.score == null ? 'UNAVAILABLE'
            : esc(env.heat.score) + ' — ' + esc(env.heat.level)) + '</b></div>' +
        '<div class="fg-kv"><span>Water deficit</span><b>' +
          (env.water.score == null ? 'UNAVAILABLE'
            : esc(env.water.score) + ' — ' + esc(env.water.level)) + '</b></div>' +
        '<div class="fg-kv"><span>River level</span><b>' +
          (z.river && z.river.available
            ? Number(z.river.level_max_m).toFixed(2) + ' m'
            : 'UNAVAILABLE') + '</b></div>' +

        '<h4>Prevention</h4>' +
        '<div class="fg-kv"><span>Priority</span><b style="color:' +
          (prev.priority === 'URGENT' ? '#e74c3c' : prev.priority === 'HIGH' ? '#e67e22' : '#2ecc71') +
          '">' + esc(prev.priority) + '</b></div>' +
        (prev.recommended_actions.length
          ? '<ul class="check-list">' + prev.recommended_actions.slice(0, 4).map(a =>
              '<li class="check-item">' +
              '<span class="check-mark">✓</span>' +
              '<span class="check-txt">' + esc(a) + '</span></li>').join('') +
            '</ul>'
          : '') +

        '<button class="btn" id="fg-analyze-zone" style="margin-top:16px;width:100%">Analyze This Zone</button>' +
      '</div>';

    const btn = document.getElementById("fg-analyze-zone");
    btn.addEventListener("click", function () {
      localStorage.setItem("fg_jump",
        JSON.stringify({ grid: gid, date: state.date, time: "14:00",
                         target: "analyze" }));
      window.location.href = "analyze.html";
    });

    // highlight the clicked dot
    document.querySelectorAll(".map-zone").forEach(g => {
      g.style.opacity = g.dataset.grid === gid ? "1" : ".45";
    });
  }

/* ---------- FORECAST ---------- */
  async function pageForecast() {
    await ensureGrids();

    const gridSel = document.getElementById("fc-grid");
    const dateInp = document.getElementById("fc-date");
    const runBtn = document.getElementById("fc-run");
    const results = document.getElementById("fc-results");
    if (!gridSel || !dateInp || !runBtn || !results) return;

    buildZoneSelect(gridSel);
    gridSel.value = state.grid;

    // jump handoff from History / Live Map
    try {
      const jump = JSON.parse(localStorage.getItem("fg_jump") || "null");
      if (jump && jump.grid) {
        state.grid = jump.grid;
        state.date = jump.date || state.date;
        gridSel.value = jump.grid;
        if (jump.date) dateInp.value = jump.date;
      }
      localStorage.removeItem("fg_jump");
    } catch (e) {}

    function loadForecast() {
      state.grid = gridSel.value;
      state.date = dateInp.value;
      renderForecast(results);
    }

    runBtn.addEventListener("click", loadForecast);
    gridSel.addEventListener("change", loadForecast);
    dateInp.addEventListener("change", loadForecast);

    // auto-run once
    loadForecast();
  }

  async function renderForecast(results) {
    loading(results, "forecast analysis");
    const j = await FGApi.analyzeRisk({
      grid_id: state.grid,
      date: state.date,
      time: "14:00"
    }).catch(() => null);

    if (!j) { offline(results); return; }
    if (j.status === "UNAVAILABLE") {
      results.innerHTML =
        '<section class="fc-card"><h3>Unavailable</h3>' +
        '<p class="form-note">' + esc(j.reason) + '</p>' +
        '<p class="form-note">Try a date between ' +
        esc((j.data_range || []).join(' and ')) + '</p></section>';
      return;
    }

    const zn = window.zoneName ? zoneName(j.grid_id) : j.grid_id;
    const isPred = j.mode === "PREDICTION";
    const badge = isPred
      ? '<span class="fg-badge-replay" style="background:#e67e22">PREDICTION</span>'
      : '';
    const levelCol = levelColor(j.risk.level);

    results.innerHTML =

      '<section class="fc-card">' +
        '<div class="panel-head"><h3>' + esc(zn) + '</h3>' + badge + '</div>' +
        '<div class="fc-kv"><span>Risk score</span><b style="color:' + levelCol + '">' +
          esc(j.risk.score) + ' / 100</b></div>' +
        '<div class="fc-kv"><span>Level</span><b style="color:' + levelCol + '">' +
          esc(j.risk.level) + '</b></div>' +
        '<div class="fc-kv"><span>Trend</span><b>' + esc(j.risk.trend || 'n/a') + '</b></div>' +
        '<div class="fc-kv"><span>Date</span><b>' + esc(j.date) + '</b></div>' +
      '</section>' +

      '<section class="fc-card">' +
        '<div class="panel-head"><h3>Risk components</h3></div>' +
        fcBar('Anomaly', j.risk.components.anomaly, 45) +
        fcBar('Temporal rainfall', j.risk.components.temporal_rainfall, 30) +
        fcBar('Vulnerability', j.risk.components.vulnerability, 25) +
      '</section>' +

      '<section class="fc-card">' +
        '<div class="panel-head"><h3>Vulnerability</h3></div>' +
        '<div class="fc-kv"><span>Score</span><b>' +
          esc(j.vulnerability.score) + ' / 100 — ' + esc(j.vulnerability.level) + '</b></div>' +
        (j.vulnerability.factors && j.vulnerability.factors.length
          ? '<ul class="check-list">' + j.vulnerability.factors.map(f =>
              '<li class="check-item"><span class="check-mark">→</span>' +
              '<span class="check-txt">' + esc(f) + '</span></li>').join('') + '</ul>'
          : '') +
      '</section>' +

      '<section class="fc-card">' +
        '<div class="panel-head"><h3>Environment</h3></div>' +
        '<div class="fc-kv"><span>Heat exposure</span><b>' +
          (j.environment.heat.score == null ? 'UNAVAILABLE'
            : esc(j.environment.heat.score) + ' — ' + esc(j.environment.heat.level)) + '</b></div>' +
        '<div class="fc-kv"><span>Water deficit</span><b>' +
          (j.environment.water.score == null ? 'UNAVAILABLE'
            : esc(j.environment.water.score) + ' — ' + esc(j.environment.water.level)) + '</b></div>' +
      '</section>' +

      '<section class="fc-card">' +
        '<div class="panel-head"><h3>Prevention</h3></div>' +
        '<div class="fc-kv"><span>Priority</span><b style="color:' +
          (j.prevention.priority === 'URGENT' ? '#e74c3c'
            : j.prevention.priority === 'HIGH' ? '#e67e22' : '#2ecc71') +
          '">' + esc(j.prevention.priority) + '</b></div>' +
        (j.prevention.recommended_actions && j.prevention.recommended_actions.length
          ? '<ul class="check-list">' + j.prevention.recommended_actions.slice(0, 5).map(a =>
              '<li class="check-item"><span class="check-mark">✓</span>' +
              '<span class="check-txt">' + esc(a) + '</span></li>').join('') + '</ul>'
          : '') +
      '</section>' +

      '<section class="fc-card">' +
        '<div class="panel-head"><h3>Why this score?</h3></div>' +
        '<ul class="check-list">' + (j.why || []).map(w =>
          '<li class="check-item"><span class="check-mark">→</span>' +
          '<span class="check-txt">' + esc(w) + '</span></li>').join('') + '</ul>' +
      '</section>' +

      '<p class="form-note" style="text-align:center">' + esc(j.disclaimer || '') + '</p>' +
      '<button class="btn" style="width:100%" onclick="window.location.href=' +
        "'analyze.html?grid=" + esc(j.grid_id) + "&date=" + esc(j.date) + "'" +
        '">Open in Analyze Risk →</button>';

    // highlight active zone on live map if linked
    document.querySelectorAll(".map-zone").forEach(g => {
      g.style.opacity = g.dataset.grid === state.grid ? "1" : ".45";
    });
  }

  function fcBar(label, value, weight) {
    return '<div style="margin:10px 0">' +
      '<div class="fc-kv"><span>' + esc(label) +
      ' <span class="mono">(' + weight + '%)</span></span>' +
      '<b>' + Number(value).toFixed(1) + '</b></div>' +
      '<div class="fc-bar"><i style="width:' + Number(value).toFixed(1) + '%"></i></div></div>';
  }

  /* ---------- ACTIONS ---------- */
  async function pageActions() {
    await ensureGrids();
    const cols = qs(".action-cols");
    if (!cols) return;

    const controls = document.createElement("div");
    controls.style.cssText = "display:flex;gap:12px;flex-wrap:wrap;margin-bottom:14px";
    const sel = buildZoneSelect();
    sel.id = "fg-actions-grid";
    sel.style.cssText = "background:#22303A;color:var(--ink,#fff);padding:12px 16px;border-radius:999px;border:1px solid var(--line)";
    sel.setAttribute("aria-label", "Zone selection");
    sel.addEventListener("change", () => { state.grid = sel.value; render(); });
    const dateInp = buildDateInput("fg-actions-date");
    dateInp.addEventListener("change", () => {
      if (dateInp.value) { state.date = dateInp.value; render(); }
    });
    controls.appendChild(sel);
    controls.appendChild(dateInp);
    cols.parentNode.insertBefore(controls, cols);

    const panel = document.createElement("section");
    panel.className = "reveal-block";
    panel.style.marginBottom = "28px";
    panel.id = "fg-prevention";
    loading(panel, "prevention recommendations");
    cols.parentNode.insertBefore(panel, cols);

    async function render() {
      // citizen-report count for THIS zone feeds Module 3 escalation rules
      let count = 0;
      try {
        const reps = await FGApi.getReports(state.grid);
        count = (reps.reports || []).filter(
          x => x.grid_id === state.grid).length;
      } catch (e) {}
      let pWrap;
      try {
        pWrap = await FGApi.getPrevention(state.grid, state.date, count);
      } catch (e) { return offline(panel); }
      const p = pWrap.prevention || pWrap;

      panel.innerHTML =
        '<div class="panel-head"><h3>Prevention recommendations — ' +
        esc(p.grid_id) + "</h3>" + replayBadge() + "</div>" +
        '<p class="form-note">Priority: <b>' + esc(p.priority) +
        "</b> · citizen reports considered: <b>" + esc(count) +
        "</b> · source: " + esc(p.rules_source || "rule_based") + "</p>" +
        (p.recommended_actions.length
          ? '<ul class="check-list">' + p.recommended_actions.map(a =>
              '<li class="check-item"><span class="check-mark">✓</span>' +
              '<span class="check-txt">' + esc(a) + "</span></li>").join("") +
            "</ul>"
          : '<p class="form-note">No actions triggered for this context.</p>') +
        '<p class="form-note"><b>Checklist:</b> ' +
        (p.checklist && p.checklist.length
          ? p.checklist.map(esc).join(" · ")
          : "—") + "</p>" +
        ((p.triggered_rules && p.triggered_rules.length)
          ? "<details open><summary class='mono'>Why these actions? " +
            "(rule trace)</summary><ul class='check-list'>" +
            p.triggered_rules.map(t =>
              "<li class='check-item'><span class='check-mark'>§</span>" +
              "<span class='check-txt'><b>Rule " + esc(t.rule_id) + "</b>: " +
              esc(t.condition) + "<br>Action: " + esc(t.action) +
              "<br><i>" + esc(t.explanation) + "</i></span></li>").join("") +
            "</ul></details>"
          : "");
    }
    await render();
  }

  /* ---------- ANALYZE (central risk workflow) ---------- */
  async function pageAnalyze() {
    await ensureGrids();
    const form = document.getElementById("fg-analyze-form");
    const gridSel = document.getElementById("fa-grid");
    buildZoneSelect(gridSel);

    // verified-event shortcuts -> fill inputs (still calls the API on submit)
    try {
      const ev = await FGApi.getHistoryEvents();
      const host = document.getElementById("fg-event-shortcuts");
      host.innerHTML = ev.events.map(e =>
        '<button type="button" class="pill" style="cursor:pointer;margin:2px"' +
        ' data-d="' + esc(e.start_date) + '">' + esc(e.start_date) +
        "</button>").join("");
      host.querySelectorAll("[data-d]").forEach(b =>
        b.addEventListener("click", () => {
          document.getElementById("fa-date").value = b.getAttribute("data-d");
        }));
    } catch (e) { /* shortcuts optional */ }

    // URL handoff (?grid=&date=&time= from map / history)
    const usp = new URLSearchParams(location.search);
    if (usp.get("grid")) { state.grid = usp.get("grid"); gridSel.value = state.grid; }
    if (usp.get("date")) { state.date = usp.get("date"); }
    document.getElementById("fa-date").value =
      usp.get("date") || FG_DATASET.DEFAULT_DATE;
    if (usp.get("time")) document.getElementById("fa-time").value = usp.get("time");

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      runAnalysis({
        grid_id: gridSel.value,
        date: document.getElementById("fa-date").value,
        time: document.getElementById("fa-time").value || "14:00"
      });
    });

    document.getElementById("fa-demo").addEventListener("click", function () {
      gridSel.value = "PUNE_G004";
      document.getElementById("fa-date").value = "2024-07-15";
      document.getElementById("fa-time").value = "14:00";
      form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(
        new Event("submit", { cancelable: true }));
    });
    const demo2 = document.getElementById("fa-demo2");
    if (demo2) demo2.addEventListener("click", function () {
      gridSel.value = "PUNE_G001";
      document.getElementById("fa-date").value = "2024-07-15";
      document.getElementById("fa-time").value = "14:00";
      form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(
        new Event("submit", { cancelable: true }));
    });

    // auto-run once with the default (verified) observation
    form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(
      new Event("submit", { cancelable: true }));
  }

  function analyzeOffline() {
    const res = document.getElementById("fg-analyze-results");
    if (res) res.innerHTML =
      '<section class="panel"><p class="form-note" style="color:#e07a5f">' +
      "BACKEND OFFLINE — Unable to connect to FloodGuard backend.</p></section>";
  }

  async function runAnalysis(payload) {
    const res = document.getElementById("fg-analyze-results");
    const stages = [
      "Retrieving zone data…",
      "Running risk assessment…",
      "Preparing prevention recommendations…",
      "Preparing environmental assessment…"
    ];
    let si = 0;
    loading(res, stages[0]);
    const timer = setInterval(() => {
      si = (si + 1) % stages.length;
      loading(res, stages[si]);
    }, 450);

    let j;
    try { j = await FGApi.analyzeRisk(payload); }
    catch (e) {
      clearInterval(timer);
      res.innerHTML =
        '<section class="panel fg-result-card">' +
        "<h3>BACKEND UNAVAILABLE</h3>" +
        '<p class="form-note" style="color:#e07a5f">Unable to reach the ' +
        "FloodGuard analysis service. Please confirm the backend is running " +
        "(uvicorn on port 8000) and try again.</p></section>";
      return;
    }
    clearInterval(timer);

    if (j.status === "UNAVAILABLE") {
      res.innerHTML =
        '<section class="panel fg-result-card"><h3>ANALYSIS UNAVAILABLE</h3>' +
        "<p class=\"form-note\">" + esc(j.reason) + "</p>" +
        '<p class="form-note">Covered range: ' + esc((j.data_range || []).join(" to ")) +
        "</p></section>";
      return;
    }

    j._badge_mode = j.mode; try { renderAnalysis(j); }
    catch (e) {
      console.error("renderAnalysis failed:", e);
      res.innerHTML =
        '<section class="panel fg-result-card">' +
        "<h3>RISK ANALYSIS FAILED</h3>" +
        '<p class="form-note" style="color:#e07a5f">Backend returned data but ' +
        "rendering failed: " + esc(String(e && e.message || e)) +
        "</p><p class=\"form-note\">Raw response has been logged to the console.</p>" +
        "</section>";
      return;
    }
    res.insertAdjacentHTML("beforeend",
      '<p class="form-note"><b>Analysis complete.</b></p>');
  }

  function bar(label, value, weightNote) {
    return '<div style="margin:10px 0"><div class="fg-kv"><span>' + esc(label) +
      (weightNote ? ' <span class="mono">(' + esc(weightNote) + ")</span>" : "") +
      "</span><b>" + Number(value).toFixed(2) + '</b></div>' +
      '<div class="fg-bar"><i style="width:' + Number(value).toFixed(1) +
      '%"></i></div></div>';
  }

  function levelColor(level) {
    if (level === "LOW") return "#2ecc71";
    if (level === "MODERATE") return "#f1c40f";
    if (level === "HIGH") return "#e67e22";
    return "#e74c3c";
  }

  function renderAnalysis(j, payload) {
    const BADGE = replayBadge(j.mode);

    const host0 = qs(".content-wrap.stack");
    if (host0) {
      const existingPipe = document.getElementById("fg-pipe-panel");
      if (!existingPipe) {
        const pipe = document.createElement("section");
        pipe.id = "fg-pipe-panel";
        pipe.className = "panel";
        pipe.style.marginTop = "22px";
        pipe.innerHTML =
          '<div class="panel-head"><h3>NOTIFICATION PIPELINE</h3>' +
          '<span class="pill">ViaSocket</span></div>' +
          '<ul class="check-list">' +
          '<li class="check-item"><span class="check-mark">1</span><span class="check-txt">Risk Engine - zone risk computed from verified data</span></li>' +
          '<li class="check-item"><span class="check-mark">2</span><span class="check-txt">Alert Engine - level + prevention priority</span></li>' +
          '<li class="check-item"><span class="check-mark">3</span><span class="check-txt">ViaSocket - webhook delivery <b>verified (HTTP 200)</b></span></li>' +
          '<li class="check-item"><span class="check-mark">4</span><span class="check-txt">Email - configured in ViaSocket workflow; demo sent, receipt pending inbox confirmation</span></li>' +
          '<li class="check-item"><span class="check-mark">5</span><span class="check-txt">SMS / WhatsApp - connectors not configured (NOT TESTED)</span></li>' +
          "</ul>" +

        host0.appendChild(pipe);
      }
    }
const auth = window.FGAuthStorage ? FGAuthStorage.get() : {};
    const isMuni = auth.role === "MUNICIPAL";
    const res = document.getElementById("fg-analyze-results");

    const zn = window.zoneName ? zoneName(j.grid_id) : j.grid_id;

    const vulnCard =
      '<section class="panel fg-result-card"><div class="panel-head">' +
      "<h3>VULNERABILITY ASSESSMENT</h3><span class=\"pill\">Module 1</span></div>" +
      '<div class="fg-kv"><span>Zone</span><b>' + esc(zn) +
      ' <span class="mono">(' + esc(j.grid_id) + ')</span></b></div>' +
      '<div class="fg-kv"><span>Vulnerability score</span><b>' +
      esc(j.vulnerability.score) + " / 100</b></div>" +
      '<div class="fg-kv"><span>Level</span><b>' + esc(j.vulnerability.level) +
      "</b></div>" +
      '<div class="fg-kv"><span>Model</span><b>' + esc(j.vulnerability.model) +
      "</b></div>" +
      '<div class="fg-kv"><span>Target</span><b>' +
      esc(j.vulnerability.target_type) + "</b></div>" +
      (j.vulnerability.xgboost_proxy_score != null
        ? '<div class="fg-kv"><span>XGBoost proxy score</span><b>' +
          esc(j.vulnerability.xgboost_proxy_score) + " / 100</b></div>"
        : "") +
      '<h3 style="margin-top:16px">Why is this zone vulnerable?</h3>' +
      '<ol class="check-list">' + (j.vulnerability.factors || []).map(f =>
        '<li class="check-item"><span class="check-mark">→</span>' +
        '<span class="check-txt">' + esc(f) + "</span></li>").join("") +
      "</ol>" +
      "</section>";

    const compRows = [
      bar("Anomaly score", j.risk.components.anomaly, "45% weight"),
      bar("Temporal rainfall signal", j.risk.components.temporal_rainfall,
          "30% weight"),
      bar("Vulnerability index", j.risk.components.vulnerability, "25% weight")
    ].join("");

    const riskCard =
      '<section class="panel fg-result-card"><div class="panel-head">' +
      "<h3>DYNAMIC RISK</h3><span class=\"pill\">Module 2</span></div>" +
      '<div class="fg-kv"><span>Risk Score</span><b>' + esc(j.risk.score) +
      " / 100</b></div>" +
      '<div class="fg-kv"><span>Risk Level</span><b style="color:' +
      levelColor(j.risk.level) + '">' + esc(j.risk.level) + "</b></div>" +
      '<div class="fg-kv"><span>Trend</span><b>' + esc(j.risk.trend ||
        "Insufficient history for trend (warm-up period)") + "</b></div>" +
      compRows +
      (BADGE ? '<p>' + BADGE + '</p>' : '') +
      "</section>";

    const whyCard =
      '<section class="panel fg-result-card"><div class="panel-head">' +
      "<h3>WHY IS THE RISK " + esc(j.risk.level) + "?</h3>" +
      '<span class="pill">from actual backend values</span></div>' +
      '<ul class="check-list">' + (j.why || []).map(w =>
        '<li class="check-item"><span class="check-mark">→</span>' +
        '<span class="check-txt">' + esc(w) + "</span></li>").join("") +
      "</ul>" +
      ((j.why || []).length ? "" :
        '<p class="form-note">Detailed explanation unavailable.</p>') +
      "</section>";

    const prev = j.prevention;
    const prevCard =
      '<section class="panel fg-result-card"><div class="panel-head">' +
      "<h3>RECOMMENDED ACTIONS</h3><span class=\"pill\">Module 3</span></div>" +
      '<div class="fg-kv"><span>Priority</span><b>' + esc(prev.priority) +
      "</b></div>" +
      (prev.recommended_actions.length
        ? '<ul class="check-list">' + prev.recommended_actions.map(a =>
            '<li class="check-item"><span class="check-mark">✓</span>' +
            '<span class="check-txt">' + esc(a) + "</span></li>").join("") +
          "</ul>"
        : '<p class="form-note">No actions triggered for this context.</p>') +
      (prev.checklist && prev.checklist.length
        ? "<h3 style='margin-top:14px'>Checklist</h3><ul class='check-list'>" +
          prev.checklist.map(c => '<li class="check-item">' +
            '<span class="check-mark">☐</span><span class="check-txt">' +
            esc(c) + "</span></li>").join("") + "</ul>"
        : "") +
      ((prev.triggered_rules || []).length
        ? "<details style='padding:0 4px'><summary class='mono'>" +
          "Rule trace (" + prev.triggered_rules.length + " rules)</summary>" +
          "<ul class='check-list'>" + prev.triggered_rules.map(t =>
            '<li class="check-item"><span class="check-mark">§</span>' +
            '<span class="check-txt"><b>Rule ' + esc(t.rule_id) + "</b>: " +
            esc(t.condition) + "<br>Action: " + esc(t.action) +
            "<br><i>" + esc(t.explanation) + "</i></span></li>").join("") +
          "</ul></details>"
        : "") +
      "</section>";

    const env = j.environment;
    const ds = env.data_status || {};
    const envCard =
      '<section class="panel fg-result-card"><div class="panel-head">' +
      "<h3>ENVIRONMENTAL CONDITIONS</h3><span class=\"pill\">Module 4</span></div>" +
      '<div class="grid-2">' +
      '<div class="fg-kv" style="display:block"><span>HEAT EXPOSURE (' +
      esc(env.heat.type) + ")</span><b>" +
      (env.heat.score == null ? "UNAVAILABLE" : esc(env.heat.score) + " / 100 - " +
       esc(env.heat.level)) + "</b></div>" +
      '<div class="fg-kv" style="display:block;margin-top:10px">' +
      "<span>WATER DEFICIT (" + esc(env.water.type) + ")</span><b>" +
      (env.water.score == null ? "UNAVAILABLE — insufficient prior-year data"
       : esc(env.water.score) + " / 100 - " + esc(env.water.level)) +
      "</b></div></div>" +
      "</section>";

    const prettyDate = new Date(j.date + "T00:00:00")
      .toLocaleDateString("en-IN", { day: "numeric", month: "long",
                                     year: "numeric" });

    /* FINAL SUMMARY */
    const summaryTitle = j.mode === "PREDICTION"
      ? "FORECAST / PREDICTION"
      : "RISK ASSESSMENT";
    const summary =
      '<section class="panel fg-result-card fg-summary">' +
      "<h3>" + summaryTitle + "</h3>" +
      '<p class="mono">' + esc(zn) + " · " + esc(prettyDate) + " · " +
      esc(j.time) + "</p>" +
      '<div style="font-size:1.5rem;font-weight:800;color:' +
      levelColor(j.risk.level) + ';margin:8px 0">' + esc(j.risk.level) +
      " — " + esc(j.risk.score) + " / 100</div>" +
      '<div class="fg-kv"><span>Trend</span><b>' + esc(risk_trend_txt(j)) +
      "</b></div>" +
      '<div class="fg-kv"><span>Vulnerability</span><b>' +
      esc(j.vulnerability.level) + "</b></div>" +
      '<div class="fg-kv"><span>Environmental heat / water</span><b>' +
      (env.heat.score == null ? "UNAVAILABLE" : esc(env.heat.score)) + " / " +
      (env.water.score == null ? "UNAVAILABLE" : esc(env.water.score)) +
      "</b></div>" +
      '<div class="fg-kv"><span>Prevention priority</span><b>' +
      esc(prev.priority) + "</b></div>" +
      "<h3 style='margin-top:16px'>WHY?</h3>" +
      '<ul class="check-list">' + (j.why || []).map(w =>
        '<li class="check-item"><span class="check-mark">→</span>' +
        '<span class="check-txt">' + esc(w) + "</span></li>").join("") +
      "</ul>" +
      "<h3 style='margin-top:16px'>WHAT SHOULD BE DONE?</h3>" +
      '<ul class="check-list">' + prev.recommended_actions.map(a =>
        '<li class="check-item"><span class="check-mark">✓</span>' +
        '<span class="check-txt">' + esc(a) + "</span></li>").join("") +
      "</ul>" +
      "</section>";

    let html = summary + vulnCard + riskCard + whyCard + prevCard + envCard;

    if (!isMuni) {
      html +=
        '<section class="panel fg-result-card"><div class="panel-head">' +
        "<h3>WHAT THIS MEANS FOR YOU</h3>" +
        '<span class="pill">PUBLIC view</span></div>' +
        '<p style="font-size:1.05rem">' + esc(j.alert_recommendation) + "</p>" +
        '<p class="fg-disclosure">Sign in as MUNICIPAL on the Alerts page for ' +
        "the operational assessment (components, checklists, citizen reports). " +
        "Sign out guests always receive the simplified view.</p></section>";
    }

    res.innerHTML = html;

    function risk_trend_txt(jj) {
      return jj.risk.trend || "Insufficient history for trend (warm-up period)";
    }
  }
  async function pageAlerts() {
    const host = qs(".content-wrap.stack");
    if (!host) return;
    host.innerHTML = "";

    const auth = window.FGAuthStorage ? FGAuthStorage.get() : {};

    // Not logged in → show ONLY login form, no header
    if (!auth.token || !auth.role) {
      const loginSec = document.createElement("section");
      loginSec.className = "panel";
      loginSec.innerHTML =
        '<div class="panel-head"><h3>Sign In</h3></div>' +
        '<form class="sub-form" style="padding:16px 20px;display:flex;gap:10px;flex-wrap:wrap;align-items:end" id="fg-login">' +
        '<div><label style="font-size:.8em;color:var(--text-3);display:block;margin-bottom:4px">Username</label>' +
        '<input id="fg-user" required placeholder="username" style="min-width:140px"></div>' +
        '<div><label style="font-size:.8em;color:var(--text-3);display:block;margin-bottom:4px">Password</label>' +
        '<input id="fg-pass" type="password" required placeholder="password" style="min-width:140px"></div>' +
        '<div><label style="font-size:.8em;color:var(--text-3);display:block;margin-bottom:4px">Role</label>' +
        '<select id="fg-rolepick" style="padding:10px 14px;border-radius:8px;border:1px solid var(--line);background:var(--bg-2);color:var(--text)">' +
        '<option value="public">PUBLIC</option>' +
        '<option value="municipal">MUNICIPAL</option></select></div>' +
        '<button class="btn" type="submit">Sign in</button></form>' +
        '<p class="form-note" style="padding:0 20px 14px">PUBLIC: citizen / citizen-demo · MUNICIPAL: municipal / municipal-demo</p>';
      host.appendChild(loginSec);

      document.getElementById("fg-login").addEventListener("submit", async function(e) {
        e.preventDefault();
        const u = document.getElementById("fg-user").value;
        const p = document.getElementById("fg-pass").value;
        const role = document.getElementById("fg-rolepick").value;
        try {
          const res = role === "municipal"
            ? await FGApi.loginMunicipal(u, p) : await FGApi.loginPublic(u, p);
          FGAuthStorage.save(res.access_token, res.role, res.username);
          window.location.href = "live-map.html";
        } catch (err) { showToast("Login failed: " + err.message); }
      });
      return;
    }

    // ── LOGGED IN ──
    const isMuni = auth.role === "MUNICIPAL";

    // Header
    const header = document.createElement("section");
    header.className = "panel";
    header.innerHTML =
      '<div class="panel-head"><h3>' + (isMuni ? "MNC Dashboard" : "Alerts") + '</h3>' +
      '<span class="pill" style="background:' + (isMuni ? "#FFD166;color:#18211F" : "#73e0a5;color:#18211F") + '">' +
      esc(auth.role) + '</span></div>' +
      '<div style="padding:0 20px 14px;color:var(--text-2)">' + esc(auth.username) + ' · ' + esc(state.date) + '</div>';
    host.appendChild(header);

    if (!isMuni) {
      let data;
      try { data = await FGApi.getPublicAlerts(state.date, null, auth.token); }
      catch (e) { return offline(host); }
      const rows = data.alerts || [];

      const sec = document.createElement("section");
      sec.className = "panel";
      let body = '<div class="panel-head"><h3>Your Alerts</h3></div>';

      if (!rows.length) {
        body += '<p style="padding:0 20px 16px;color:var(--text-2)">No alerts for this date.</p>';
      } else {
        body += rows.map(a => {
          const m = a.message || {};
          const items = (m.what_to_do || []).map(i => '<li style="margin:3px 0">• ' + esc(i) + '</li>').join("");
          return '<div style="border:1px solid var(--line);border-radius:8px;padding:12px 16px;margin:0 20px 10px;background:rgba(255,255,255,0.02)">' +
            '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">' +
            '<b>' + esc(m.headline || a.grid_id) + '</b>' +
            '<span class="lvl-tag lvl-' + esc(a.risk_level.toLowerCase()) + '">' + esc(a.risk_level) + '</span></div>' +
            '<p style="color:var(--accent);font-weight:600;margin:4px 0">' + esc(m.status || "") + '</p>' +
            '<p style="margin:4px 0;color:var(--text-2)">' + esc(m.what_happening || "") + '</p>' +
            (items ? '<ul style="padding-left:18px;margin:6px 0 0;color:var(--text-2)">' + items + '</ul>' : '') +
            '</div>';
        }).join("");
      }
      sec.innerHTML = body;
      host.appendChild(sec);
      return;
    }

    // ── MNC ──

    // Send Public Alerts
    const sendPubSec = document.createElement("section");
    sendPubSec.className = "panel";
    sendPubSec.innerHTML =
      '<div class="panel-head"><h3>Send Public Alerts</h3><span class="pill">ViaSocket → Public Email Gateway</span></div>' +
      '<div style="padding:16px 20px">' +
      '<p style="color:var(--text-2);margin-bottom:14px">Send reassuring flood safety alerts to citizens in all 4 zones. Tone: calm, action-oriented, no panic.</p>' +
      '<button class="btn" id="fg-trigger-public" style="min-width:200px">Send Public Alerts</button>' +
      '<div id="fg-pub-alert-status" style="margin-top:12px"></div></div>';
    host.appendChild(sendPubSec);

    document.getElementById("fg-trigger-public").addEventListener("click", async function() {
      const btn = this;
      const status = document.getElementById("fg-pub-alert-status");
      btn.disabled = true;
      btn.textContent = "Sending...";
      status.innerHTML = '<p class="form-note">Generating public alerts for 4 zones...</p>';
      try {
        const res = await FGApi.generateAlerts(state.date, "public");
        const vs = res.viasocket_results || [];
        const ok = vs.filter(v => v.status === "delivered").length;
        const fail = vs.filter(v => v.status === "error").length;
        status.innerHTML =
          '<p style="color:#73e0a5">Public alerts sent: ' + ok + '/' + vs.length + ' webhooks delivered</p>' +
          (fail ? '<p style="color:#ef4444">' + fail + ' failed</p>' : '');
        btn.textContent = "Sent!";
        setTimeout(() => { btn.disabled = false; btn.textContent = "Send Public Alerts"; }, 2000);
      } catch (err) {
        status.innerHTML = '<p style="color:#ef4444">Failed: ' + esc(err.message) + '</p>';
        btn.disabled = false;
        btn.textContent = "Send Public Alerts";
      }
    });

    // Send Municipal Internal Alerts
    const sendMunSec = document.createElement("section");
    sendMunSec.className = "panel";
    sendMunSec.innerHTML =
      '<div class="panel-head"><h3>Municipal Internal Alerts</h3><span class="pill">ViaSocket → Municipal Email Gateway</span></div>' +
      '<div style="padding:16px 20px">' +
      '<p style="color:var(--text-2);margin-bottom:14px">Send blunt operational alerts to MNC disaster teams. Tone: direct, exact numbers, component scores, action items.</p>' +
      '<button class="btn" id="fg-trigger-municipal" style="min-width:200px;background:#e67e22;border-color:#e67e22">Send Municipal Internal Alerts</button>' +
      '<div id="fg-mun-alert-status" style="margin-top:12px"></div></div>';
    host.appendChild(sendMunSec);

    document.getElementById("fg-trigger-municipal").addEventListener("click", async function() {
      const btn = this;
      const status = document.getElementById("fg-mun-alert-status");
      btn.disabled = true;
      btn.textContent = "Sending...";
      status.innerHTML = '<p class="form-note">Generating municipal alerts for 4 zones...</p>';
      try {
        const res = await FGApi.generateAlerts(state.date, "municipal");
        const vs = res.viasocket_results || [];
        const ok = vs.filter(v => v.status === "delivered").length;
        const fail = vs.filter(v => v.status === "error").length;
        status.innerHTML =
          '<p style="color:#73e0a5">Municipal alerts sent: ' + ok + '/' + vs.length + ' webhooks delivered</p>' +
          (fail ? '<p style="color:#ef4444">' + fail + ' failed</p>' : '');
        btn.textContent = "Sent!";
        setTimeout(() => { btn.disabled = false; btn.textContent = "Send Municipal Internal Alerts"; }, 2000);
      } catch (err) {
        status.innerHTML = '<p style="color:#ef4444">Failed: ' + esc(err.message) + '</p>';
        btn.disabled = false;
        btn.textContent = "Send Municipal Internal Alerts";
      }
    });

    // MNC Internal Alerts
    let data;
    try { data = await FGApi.getMunicipalAlerts(state.date, null, 0, auth.token); }
    catch (e) { return offline(host); }
    const rows = data.alerts || [];

    const mncSec = document.createElement("section");
    mncSec.className = "panel";
    let mncBody = '<div class="panel-head"><h3>MNC Internal Alerts</h3><span class="pill">Operational</span></div>';

    if (!rows.length) {
      mncBody += '<p style="padding:0 20px 16px;color:var(--text-2)">No alerts yet. Click "Send Alerts Now" above.</p>';
    } else {
      mncBody += rows.map(m => {
        const msg = m.message || {};
        const comps = msg.components || m.risk_components || {};
        return '<div style="border:1px solid var(--line);border-radius:8px;padding:12px 16px;margin:0 20px 10px;background:rgba(255,255,255,0.02)">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">' +
          '<b>' + esc(msg.headline || m.grid_id) + '</b>' +
          '<span class="lvl-tag">' + esc(m.risk_level || "?") + '</span></div>' +
          '<p style="color:var(--accent);font-weight:600;margin:4px 0">' + esc(msg.situation || "") + '</p>' +
          '<p style="margin:4px 0;color:var(--text-2)"><b>Action:</b> ' + esc(msg.action_required || m.prevention_priority) + '</p>' +
          '<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px;font-size:.85em;color:var(--text-2)">' +
          '<div>Anomaly: ' + esc(comps.anomaly || "?") + '</div>' +
          '<div>Rainfall: ' + esc(comps.temporal_rainfall || "?") + '</div>' +
          '<div>Vulnerability: ' + esc(comps.vulnerability || "?") + '</div>' +
          '<div>Reports: ' + esc(m.citizen_reports || 0) + '</div></div></div>';
      }).join("");
    }

    mncSec.innerHTML = mncBody;
    host.appendChild(mncSec);
  }

  /* ---------- ROUTES ---------- */
  async function pageRoutes() {
    const table = qs(".route-table");
    if (!table) return;
    let z;
    try { z = await FGApi.getZone(state.grid, state.date); }
    catch (e) { return offline(table); }
    table.innerHTML =
      '<div class="route-head"><span>Safe routing</span><span>Status</span></div>' +
      '<div class="route-row"><div><div class="route-name">' +
      esc(z.routing.reason) + "</div>" +
      '<div class="route-via">Safe-route suggestions require a verified, complete ' +
      "road network. No such dataset exists in this project yet, so no routes are generated.</div></div>" +
      '<div class="route-via">—</div><div class="route-elev">—</div>' +
      '<span class="pill pill-closed route-status">UNAVAILABLE</span></div>';
  }

  /* ---------- WHY ---------- */
  async function pageWhy() {
    const gridSec = qs(".reason-grid");
    if (!gridSec) return;
    const panel = document.createElement("section");
    panel.className = "reveal-block";
    panel.style.marginTop = "34px";
    panel.id = "fg-vulnerability";
    loading(panel, "vulnerability explanation");
    gridSec.parentNode.insertBefore(panel, gridSec.nextSibling);

    let v;
    try { v = await FGApi.getVulnerability(state.grid); }
    catch (e) { return offline(panel); }
    const vul = v.vulnerability;

    panel.innerHTML =
      '<div class="panel-head"><h3>MODULE 1 — VULNERABILITY · ' +
      esc(state.grid) + '</h3><span class="pill">Module 1</span></div>' +
      '<ul class="check-list">' +
      '<li class="check-item"><span class="check-mark">①</span><span class="check-txt">' +
      "<b>Transparent Vulnerability Index:</b> score " + esc(vul.score) +
      " (" + esc(vul.level) + ")</span></li>" +
      '<li class="check-item"><span class="check-mark">②</span><span class="check-txt">' +
      "<b>Contributing factors:</b> " +
      esc((vul.explanations || []).join("; ")) + "</span></li>" +
      (vul.xgboost_proxy && vul.xgboost_proxy.score != null
        ? '<li class="check-item"><span class="check-mark">③</span>' +
          '<span class="check-txt"><b>Hydrologic Vulnerability Proxy ' +
          "(XGBoost rule-distilled):</b> " + esc(vul.xgboost_proxy.score) +
          " / 100 — an exposure estimate, <i>not</i> a flood probability</span></li>"
        : '<li class="check-item"><span class="check-mark">③</span>' +
          '<span class="check-txt"><b>XGBoost proxy:</b> unavailable</span></li>') +
      "</ul>" +
      '<div class="panel" style="padding:14px 18px;margin-top:10px">' +
      '<p class="form-note"><b>Disclosure — hydrologic vulnerability proxy.</b> ' +
      "The ML target is a disclosed rule: distance-to-drainage &le; 700 m AND " +
      "elevation below the study-area 35th percentile. Model metrics measure " +
      "agreement with that rule on real geodata. This is an exposure estimate, " +
      "<i>not</i> verified flood prediction and <i>not</i> a flood probability." +
      "</p></div>"; +
      '<p class="form-note">Exposure estimates only — never flood probability. ' +
      "Select another zone on the Forecast page to compare.</p>";
  }

  /* ---------- HISTORY ---------- */
  async function pageHistory() {
    const tl = qs(".timeline");
    if (!tl) return;
    const real = document.createElement("div");
    real.className = "timeline";
    real.style.marginBottom = "40px";
    loading(real, "verified historical events");
    tl.parentNode.insertBefore(real, tl);

    let ev;
    try { ev = await FGApi.getHistoryEvents(); }
    catch (e) { return offline(real); }
    if (!ev.events || !ev.events.length) return empty(real);

    real.innerHTML = '<h2 style="letter-spacing:-.02em;margin-bottom:14px"' +
      ">Verified historical records (2014–2016 archive)</h2>" +
      '<p class="form-note" style="margin-bottom:14px">These are the only ' +
      "verified flood dates in the project. Use “Open in Zone Risk” to jump " +
      "straight to that date on the risk page.</p>" +
      ev.events.map(e =>
        '<div class="tl-item major"><span class="tl-year mono">Event #' +
        esc(e.event_id) + " — " + esc(e.start_date) +
        (e.end_date !== e.start_date ? " → " + esc(e.end_date) : "") +
        "</span><h3>" + esc(e.main_cause) + "</h3><p>Location recorded at " +
        esc(Number(e.latitude).toFixed(4)) + "N, " +
        esc(Number(e.longitude).toFixed(4)) +
        "E (maps to PUNE_G004). Source: " + esc(e.source) + "/" +
        esc(e.district) + " log.</p>" +
        '<span class="tl-stat">Severity attributes: not available in source record</span> ' +
        '<button class="btn" style="margin-top:8px" data-jump="' +
        esc(e.start_date) + '">Open in Zone Risk</button></div>'
      ).join("") +
      '<p class="archive-note">These are the ONLY verified flood records in the ' +
      "project (5 events). Everything below is illustrative demo material.</p>";

    real.querySelectorAll("[data-jump]").forEach(btn => {
      btn.addEventListener("click", function () {
        localStorage.setItem("fg_jump",
          JSON.stringify({ date: btn.getAttribute("data-jump"),
                           grid: "PUNE_G004" }));
        window.location.href = "forecast.html";
      });
    });
  }

  const ROUTES = {
    home: pageIndex,
    "live-map": pageLiveMap,
    why: pageWhy,
    forecast: pageForecast,
    routes: pageRoutes,
    actions: pageActions,
    history: pageHistory,
    alerts: pageAlerts,
    analyze: pageAnalyze
  };

  function injectRoleBadge() {
    const nav = qs(".site-header .nav-links");
    if (!nav || document.getElementById("fg-user-menu")) return;

    const auth = window.FGAuthStorage ? FGAuthStorage.get() : {};
    const alertsLink = nav.querySelector('a[href="alerts.html"]');

    // Alerts visible only for MNC
    if (alertsLink) {
      alertsLink.style.display = (auth.role === "MUNICIPAL") ? "" : "none";
    }

    const menu = document.createElement("div");
    menu.id = "fg-user-menu";
    menu.style.cssText = "position:relative;margin-left:auto;display:inline-block";

    if (!auth.token || !auth.role) {
      menu.innerHTML =
        '<a href="alerts.html" style="padding:8px 16px;border:1px solid var(--line);border-radius:8px;color:var(--text);text-decoration:none;font-size:.9em;cursor:pointer">Sign In</a>';
    } else {
      const color = auth.role === "MUNICIPAL" ? "#FFD166" : "#73e0a5";
      menu.innerHTML =
        '<button id="fg-user-btn" style="padding:8px 16px;border:1px solid var(--line);border-radius:8px;background:' + color + ';color:#18211F;font-weight:600;cursor:pointer;font-size:.9em">' +
        esc(auth.username) + ' <span style="font-size:.75em;opacity:.7">▾</span></button>' +
        '<div id="fg-user-dropdown" style="display:none;position:absolute;right:0;top:100%;margin-top:6px;background:var(--bg-2);border:1px solid var(--line);border-radius:8px;min-width:180px;z-index:100;overflow:hidden">' +
        '<div style="padding:10px 14px;color:var(--text-3);font-size:.8em;border-bottom:1px solid var(--line)">' + esc(auth.username) + ' · ' + esc(auth.role) + '</div>' +
        '<button id="fg-signout" style="display:block;width:100%;padding:10px 14px;border:none;background:none;color:#ef4444;text-align:left;cursor:pointer;font-size:.9em">Sign Out</button>' +
        '</div>';
    }

    nav.appendChild(menu);

    const btn = document.getElementById("fg-user-btn");
    const dropdown = document.getElementById("fg-user-dropdown");
    if (btn && dropdown) {
      btn.addEventListener("click", function(e) {
        e.stopPropagation();
        dropdown.style.display = dropdown.style.display === "block" ? "none" : "block";
      });
      document.addEventListener("click", function() { dropdown.style.display = "none"; });
    }

    const signout = document.getElementById("fg-signout");
    if (signout) signout.addEventListener("click", function() {
      FGAuthStorage.clear();
      window.location.href = "login.html";
    });
  }

  function injectOfflineBanner(offline) {
    let b = document.getElementById("fg-offline-banner");
    if (offline && !b) {
      b = document.createElement("div");
      b.id = "fg-offline-banner";
      b.style.cssText =
        "position:fixed;top:0;left:0;right:0;z-index:9999;background:#c0392b;" +
        "color:#fff;text-align:center;padding:8px;font-weight:700;" +
        "font-family:'IBM Plex Mono',monospace";
      b.textContent = "BACKEND OFFLINE — Unable to connect to FloodGuard backend.";
      document.body.appendChild(b);
    } else if (!offline && b) {
      b.remove();
    }
  }

  /* ---------- CITIZEN REPORT FORM (alerts page) ---------- */
  function buildReportForm(host) {
    if (!host || document.getElementById("fg-report-form-panel")) return;
    const panel = document.createElement("section");
    panel.className = "panel";
    panel.id = "fg-report-form-panel";
    panel.innerHTML =
      '<div class="panel-head"><h3>Report an incident</h3>' +
      '<span class="pill">Citizen reporting</span></div>' +
      '<form class="sub-form" style="padding:18px 20px" id="fg-report-form">' +
      '<select id="fr-grid" required aria-label="Zone"></select>' +
      '<select id="fr-type" required aria-label="Report type">' +
      '<option value="WATERLOGGING">WATERLOGGING</option>' +
      '<option value="FLOODING">FLOODING</option>' +
      '<option value="BLOCKED_DRAIN">BLOCKED_DRAIN</option>' +
      '<option value="OTHER">OTHER</option></select>' +
      '<input id="fr-desc" required placeholder="What are you seeing?">' +
      '<button class="btn" type="submit">Submit report</button></form>' +
      '<p class="form-note" style="padding:0 20px 16px" id="fr-note">' +
      "Reports go to the FloodGuard backend and appear in municipal views.</p>" +
      '<div class="panel-head"><h3>Recent reports</h3>' +
      '<span class="pill" id="fr-count">—</span></div>' +
      '<div id="fr-list" style="padding:0 20px 18px"></div>';
    host.appendChild(panel);

    const gridSel = panel.querySelector("#fr-grid");
    GRIDS.forEach(g => {
      const o = document.createElement("option");
      o.value = g; o.textContent = g;
      gridSel.appendChild(o);
    });

    async function refreshList() {
      try {
        const rep = await FGApi.getReports();
        const list = rep.reports || [];
        panel.querySelector("#fr-count").textContent =
          list.length + " stored";
        panel.querySelector("#fr-list").innerHTML = list.slice(-5).reverse()
          .map(r => '<p class="form-note"><b>' + esc(r.report_id) + "</b> · " +
            esc(r.grid_id) + " · " + esc(r.report_type) + " · " +
            esc(r.status) + " · " + esc(String(r.timestamp).slice(0, 19)) +
            "</p>").join("") || '<p class="form-note">No reports submitted yet.</p>';
      } catch (e) { /* listing optional */ }
    }

    panel.querySelector("#fg-report-form").addEventListener("submit",
      async function (e) {
        e.preventDefault();
        try {
          const res = await FGApi.submitReport({
            grid_id: gridSel.value,
            report_type: panel.querySelector("#fr-type").value,
            description: panel.querySelector("#fr-desc").value
          });
          if (window.showToast)
            showToast("Report submitted successfully. ID " + res.report_id);
          panel.querySelector("#fr-desc").value = "";
          refreshList();
        } catch (err) {
          if (window.showToast) showToast("Unable to submit report: " + err.message);
          else alert("Unable to submit report.");
        }
      });
    refreshList();
  }

  document.addEventListener("DOMContentLoaded", async function () {
    const page = document.body.getAttribute("data-page");
    injectRoleBadge();
    let backendUp = true;
    try { await FGApi.getHealth(); }
    catch (e) { backendUp = false; }
    injectOfflineBanner(!backendUp);
    if (!backendUp) {
      const any = qs(".stats-grid, .content-wrap");
      if (any) offline(any, "");
      return;
    }
    await ensureGrids();
    const fn = ROUTES[page];
    if (!fn) return;
    try { await fn(); }
    catch (e) {
      console.error("[FloodGuard] page crashed:", e);
      if (window.fgShowError)
        fgShowError(page + " page error: " + (e && e.message || e));
      const host = qs(".content-wrap") || qs(".stats-grid");
      if (host) offline(host, "");
    }

    /* citizen report form lives on the alerts page (public capability) */
    if (page === "alerts") buildReportForm(qs(".content-wrap.stack"));
  });

  window.FGPages = { state };
})();
