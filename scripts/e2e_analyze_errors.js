/* PHASE 10 DEBUG — error-case verification against live backend. */
const BASE = "http://localhost:8000/api/risk/analyze";
const cases = [
  { name: "invalid zone PUNE_G999 -> 400",
    body: { grid_id: "PUNE_G999", date: "2024-07-15", time: "14:00" },
    expect: r => r.status === 400 },
  { name: "date outside dataset -> status UNAVAILABLE",
    body: { grid_id: "PUNE_G004", date: "2030-01-01", time: "14:00" },
    expect: async r => {
      const j = await r.json();
      return r.status === 200 && j.status === "UNAVAILABLE" &&
             /No data available/i.test(j.reason || "");
    } },
  { name: "bad time 99:99 -> 400",
    body: { grid_id: "PUNE_G004", date: "2024-07-15", time: "99:99" },
    expect: r => r.status === 400 },
  { name: "missing time -> defaults to 14:00",
    body: { grid_id: "PUNE_G004", date: "2024-07-15" },
    expect: async r => (await r.json()).time === "14:00" },
  { name: "unparseable date -> 400",
    body: { grid_id: "PUNE_G004", date: "not-a-date" },
    expect: r => r.status === 400 }
];

(async () => {
  let fail = 0;
  for (const c of cases) {
    try {
      const r = await fetch(BASE, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(c.body)
      });
      const pass = await c.expect(r);
      console.log((pass ? "PASS " : "FAIL ") + c.name +
                  `  [HTTP ${r.status}]`);
      if (!pass) fail++;
    } catch (e) {
      console.log("FAIL " + c.name + ": " + e.message);
      fail++;
    }
  }
  if (fail) process.exit(1);
  console.log("ALL ERROR CASES PASS");
})();
