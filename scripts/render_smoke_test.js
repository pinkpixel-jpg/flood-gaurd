/* Executes the REAL renderAnalysis() from pages.js in a sandbox (stubbed
   DOM) against LIVE backend responses — proves no ReferenceError/TypeError
   and that every section renders for multiple zones and both roles. */

const fs = require("fs");
const vm = require("vm");
const path = require("path");

const BASE = "http://localhost:8000/api";
const src = fs.readFileSync(
  path.join(__dirname, "..", "frontend", "js", "pages.js"), "utf8");

// extract renderAnalysis function source
const start = src.indexOf("function renderAnalysis");
if (start < 0) throw new Error("renderAnalysis not found");
let depth = 0, end = start;
for (let i = src.indexOf("{", start); i < src.length; i++) {
  if (src[i] === "{") depth++;
  else if (src[i] === "}") { depth--; if (depth === 0) { end = i + 1; break; } }
}
const fnSrc = src.slice(start, end);

function makeSandbox(role) {
  let captured = "";
  const esc = s => String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const sandbox = {
    console,
    FGAuthStorage: { get: () => ({ role, username: "sandbox" }) },
    esc, levelColor: () => "#fff",
    bar: (label, value, weight) =>
      "<div class='bar'>" + label + ":" + Number(value).toFixed(2) +
      "(" + weight + ")</div>",
    replayBadge: () => "<span class='badge'>HISTORICAL REPLAY</span>",
    document: {
      getElementById: id => ({
        set innerHTML(v) { captured += "[" + id + "]" + v; },
        querySelector: () => ({ innerHTML: "", insertAdjacentHTML(){} }),
        appendChild(){}
      }),
      createElement: () => ({ style:{}, set innerHTML(v){captured+=v;},
        appendChild(){}, querySelector:()=>({innerHTML:"",style:{}}),
        classList:{add(){}}, addEventListener(){} })
    },
    window: {}
  };
  sandbox.window = sandbox;
  // res object used by renderAnalysis via document.getElementById already;
  // but renderAnalysis reads `res` from enclosing scope -> provide directly:
  const context = vm.createContext(Object.assign(sandbox, {
    res: { set innerHTML(v) { captured = v; } }
  }));
  vm.runInContext(fnSrc, context);
  return { run: (j) => {
    context.renderAnalysis(j, {});
    return captured;
  }, context };
}

async function main() {
  const cases = [
    { grid_id: "PUNE_G004", date: "2024-07-15", time: "14:00",
      expect: ["79.22", "HIGH", "INCREASING", "URGENT"] },
    { grid_id: "PUNE_G001", date: "2024-07-15", time: "14:00",
      expect: ["83.19", "CRITICAL"] }
  ];
  let fail = 0;

  for (const c of cases) {
    const r = await fetch(BASE + "/risk/analyze", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(c)
    });
    const j = await r.json();
    for (const role of ["PUBLIC", "MUNICIPAL"]) {
      const sb = makeSandbox(role);
      let html;
      try { html = sb.run(j); }
      catch (e) { console.log(`FAIL ${c.grid_id}/${role}: ${e.message}`); fail++; continue; }

      const need = [
        ["RISK ASSESSMENT", true],
        [c.expect[0], true],
        ["VULNERABILITY ASSESSMENT", true],
        ["DYNAMIC RISK", true],
        ["WHY IS THE RISK", true],
        ["RECOMMENDED ACTIONS", true],
        ["ENVIRONMENTAL CONDITIONS", true],
        ["HISTORICAL REPLAY", true],
        ["NOT A LIVE FLOOD WARNING", true]
      ];
      const missing = need.filter(([s]) => !html.includes(s))
                          .map(([s]) => s);
      if (missing.length || /ReferenceError|is not defined/.test(html)) {
        console.log(`FAIL ${c.grid_id} (${role}): missing=${missing}`);
        fail++;
      } else {
        console.log(`PASS ${c.grid_id} (${role}): all sections rendered, ` +
          `${html.length} chars`);
      }
    }
  }
  if (fail) process.exit(1);
  console.log("RENDER SMOKE TEST: ALL PASS");
}

main().catch(e => { console.error(e); process.exit(1); });
