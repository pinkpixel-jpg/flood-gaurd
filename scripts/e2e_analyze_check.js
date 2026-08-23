(async () => {
  const r = await fetch("http://localhost:8000/api/risk/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ grid_id: "PUNE_G004", date: "2024-07-15",
                           time: "14:00" })
  });
  console.log("HTTP", r.status);
  const j = await r.json();
  const ds = j.environment.data_status || {};
  const checks = {
    risk_79_22_HIGH_INC: j.risk.score === 79.22 && j.risk.level === "HIGH" &&
                         j.risk.trend === "INCREASING",
    comps_exact: j.risk.components.anomaly === 85.31 &&
                 j.risk.components.temporal_rainfall === 91.25 &&
                 j.risk.components.vulnerability === 53.83,
    vuln_53_83_MODERATE_proxy: j.vulnerability.score === 53.83 &&
        j.vulnerability.level === "MODERATE" &&
        j.vulnerability.target_type === "Hydrologic Vulnerability Proxy",
    factors_ranked: Array.isArray(j.vulnerability.factors) &&
                    j.vulnerability.factors.length >= 3,
    prevention_URGENT_trace: j.prevention.priority === "URGENT" &&
        (j.prevention.triggered_rules || []).length >= 5,
    checklist_present: Array.isArray(j.prevention.checklist),
    env_heat_water: j.environment.heat != null && j.environment.water != null,
    telemetry_UNAVAILABLE: ds.temperature_telemetry === "UNAVAILABLE" &&
        ds.reservoir_storage_telemetry === "UNAVAILABLE",
    why_composed: Array.isArray(j.why) && j.why.length >= 3,
    mode_replay: j.mode === "HISTORICAL_REPLAY"
  };
  let fail = 0;
  for (const [k, v] of Object.entries(checks)) {
    console.log((v ? "PASS " : "FAIL ") + k);
    if (!v) fail++;
  }
  if (fail) process.exit(1);
  console.log("E2E RENDER CONTRACT: ALL PASS");
})();
