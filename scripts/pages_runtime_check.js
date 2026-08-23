/* Runtime check: executes the REAL pages.js page functions in a stubbed
   DOM against the LIVE backend — every page, both success and offline. */

const fs = require("fs");
const vm = require("vm");
const path = require("path");

const API = process.argv[2] || "http://localhost:8000/api";

const ALL_WRITES = [];
const SEL_WRITES = {};



function makeElement(tag) {
  const el = {
    tagName: (tag || "div").toUpperCase(),
    children: [], listeners: {}, style: {}, dataset: {},
    _html: "", value: "", textContent: "",
    set innerHTML(v) {
      this._html = String(v);
      ALL_WRITES.push(this._html);
      this.children = [];
    },
    get innerHTML() { return this._html; },
    set textContent(v) { this._text = String(v); },
    get textContent() { return this._text || ""; },
    appendChild(c) { this.children.push(c); return c; },
    insertAdjacentHTML(pos, html) { this._html += html; },
    insertBefore(c, ref) { this.children.push(c); return c; },
    addEventListener(type, fn) {
      (this.listeners[type] = this.listeners[type] || []).push(fn);
    },
    removeEventListener() {},
    querySelector(sel) {
      const el = makeElement("div");
      Object.defineProperty(el, "innerHTML", {
        set(v) { SEL_WRITES[sel] = String(v); ALL_WRITES.push(String(v)); },
        get() { return el._html || ""; }
      });
      return el;
    },
    querySelectorAll(sel) { return []; },
    setAttribute(k, v) { this.dataset[k] = v; },
    getAttribute(k) { return this.dataset[k] || null; },
    classList: { add(){}, remove(){}, contains(){ return false; } },
    remove() {},
    requestSubmit() { fire(this, "submit"); },
    closest() { return null; }
  };
  return el;
}
function fire(el, type, ev) {
  ev = ev || { preventDefault(){} };
  (el.listeners[type] || []).forEach(fn => fn(ev));
}

function buildContext(pageName, apiBase) {
  let capturedHtml = {};
  const documentStub = {
    body: { getAttribute: () => pageName,
            setAttribute(){}, dataset:{ page: pageName } },
    addEventListener(type, fn) {
      if (type === "DOMContentLoaded") domReadyFns.push(fn);
    },
    getElementById(id) {
      const el = makeElement("div");
      el.id = id;
      Object.defineProperty(el, "innerHTML", {
        set(v) { capturedHtml[id] = String(v); },
        get() { return capturedHtml[id] || ""; }
      });
      return el;
    },
    createElement: t => makeElement(t),
    createElementNS: (ns, t) => {
      const el = makeElement(t);
      el.setAttribute = function (k, v) { this.dataset[k] = v; };
      return el;
    },
    querySelector: sel => makeSelStub(sel),
    querySelectorAll: () => [],
    body2: null
  };
  function makeSelStub(sel) {
    const el = makeElement("div");
    el._sel = sel;
    el.parentNode = makeElement("div");
    Object.defineProperty(el, "innerHTML", {
        set(v) { SEL_WRITES[sel] = String(v); el._html = String(v); },
        get() { return el._html || ""; }
    });
    const prev = Object.getOwnPropertyDescriptor(el, "innerHTML");
    Object.defineProperty(el, "innerHTML", {
        set(v) { if (prev && prev.set) prev.set.call(el, v); SEL_WRITES[sel] = el._html || ""; },
        get() { return el._html || ""; }
    });
    // special-case: header nav for role badge
    if (sel.includes(".nav-links")) el.appendChild = c => c;
    return el;
  }

  const handlers = [];
  const domReadyFns = [];
  
  const sandboxWindow = {
    addEventListener(type) { /* window-level listeners recorded as no-op */ },
    removeEventListener() {},
    FG_API_BASE: apiBase,
    FG_API_BASE: apiBase,
    fetch: global.fetch,
    AbortSignal,
    URLSearchParams,
    console,
    setTimeout, clearTimeout, setInterval, clearInterval,
    localStorage: (() => {
      let store = {};
      return { getItem:k=>store[k]??null, setItem:(k,v)=>store[k]=String(v),
               removeItem:k=>delete store[k] };
    })(),
    location: { search: "", href: "http://x/" + pageName + ".html",
                origin: "http://localhost:8080" },
    navigator: { userAgent: "node-test" },
    matchMedia: () => ({ matches:false }),
  };
  sandboxWindow.document = Object.assign(documentStub, {
    getElementById: documentStub.getElementById
  });
  // document.addEventListener must capture DOMContentLoaded:
  const realDocAdd = documentStub.addEventListener;
  documentStub.addEventListener = function (type, fn) {
    if (type === "DOMContentLoaded") domReadyFns.push(fn);
  };
  sandboxWindow.document = documentStub;

  const ctx = vm.createContext(sandboxWindow);
  ctx.window = sandboxWindow;
  ctx.document = documentStub;
  vm.runInContext(
    fs.readFileSync(path.join(__dirname,"..","frontend","js","api.js"),"utf8"),
    ctx);
  vm.runInContext(
    fs.readFileSync(path.join(__dirname,"..","frontend","js","pages.js"),"utf8"),
    ctx);
  return {
    async boot() { for (const fn of domReadyFns.splice(0)) await fn(); },
    html: id => capturedHtml[id] || "",
    selWritesObj: () => SEL_WRITES,
    allWrites: () => ALL_WRITES,
    allHtml: () => JSON.stringify(capturedHtml),
    errors: () => []
  };
}

(async () => {
  let fail = 0;
  const pages = [
    ["home",       ["Total zones", "Replay date"]],
    ["live-map",   ["river level", "HISTORICAL REPLAY"]],
    ["forecast",   ["MODULE 2", "Anomaly score", "MODULE 4"]],
    ["why",        ["MODULE 1", "Hydrologic Vulnerability Proxy"]],
    ["actions",    ["Priority", "Rule "]],
    ["alerts",     ["Sign in to view your alerts"]],
    ["analyze",    ["RISK ASSESSMENT", "79.22"]]
  ];

  for (const [page, markers] of pages) {
    const ctx = buildContext(page, API);
    await ctx.boot();
    let lastSnap = "", stable = 0;
    for (let t = 0; t < 24; t++) {
      await new Promise(r => setTimeout(r, 250));
      const snap = JSON.stringify(ctx.html()) + ctx.allHtml();
      if (snap === lastSnap) { stable++; if (stable >= 4) break; }
      else { stable = 0; lastSnap = snap; }
    }  // let chained renders finish
    const allHtml = ctx.allHtml() + JSON.stringify(ctx.selWritesObj()) + ctx.allWrites().join('');
    const missing = markers.filter(m => !allHtml.includes(m));
    const dbg = ctx.html("fg-debug-error") + (ctx.selWritesObj()["#fg-debug-error"] || "");
    if (dbg) { fail++; console.log(`FAIL ${page}: debug error bar -> ${dbg.slice(0,200)}`); }
    else if (missing.length) {
      fail++;
      console.log(`FAIL ${page}: missing ${missing}`);
      console.log('   [fg-analyze-results] -> ' +
        String(ctx.html("fg-analyze-results"))
          .replace(/\s+/g, " ").slice(0, 200));
      const sw = ctx.selWritesObj();
      for (const [sel, v] of Object.entries(sw)) {
        console.log("   [" + sel + "] -> " +
          String(v).replace(/\s+/g," ").slice(0, 180));
      }
    }
    else console.log(`PASS ${page}: ` + markers.join(" | "));
    // offline simulation
    const offCtx = buildContext(page, "http://localhost:59999");
    await offCtx.boot();
    await new Promise(r => setTimeout(r, 300));
    const offText = JSON.stringify(offCtx.allHtml()) + JSON.stringify(offCtx.selWritesObj());
    if (!/Unable to connect|BACKEND OFFLINE|offline/i.test(offText)) {
      fail++; console.log(`FAIL ${page} offline state`);
    } else if (offCtx.html("fg-debug-error")) {
      fail++; console.log(`FAIL ${page}: offline run raised debug errors`);
    } else {
      console.log(`PASS ${page} offline state shown`);
    }
  }

  if (fail) { console.log(`FAILURES: ${fail}`); process.exit(1); }
  console.log("ALL PAGE RUNTIME CHECKS PASSED");
})().catch(e => { console.error(e); process.exit(1); });
