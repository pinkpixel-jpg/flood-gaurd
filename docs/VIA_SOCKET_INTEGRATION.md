# ViaSocket Integration (AUTOMATION layer) — Pune FloodShield

Status: ADAPTER READY + CONNECTIVITY VERIFIED (HTTP 200).
Webhook configured via env var; URL never exposed.
A TEMPORARY prototype demo branch exists for orchestration demos only.

## 1. Purpose

viaSocket is the ORCHESTRATION/AUTOMATION layer: it triggers the risk
service and delivers results onward (notifications, logging, actions).
It never performs GIS or ML computation itself.

**viaSocket = AUTOMATION / ORCHESTRATION · Python = COMPUTATION**

## 1b. CURRENT PROTOTYPE FLOW (implemented & verified)

```
Webhook
  ↓
Receive ML event  (pune.flood_risk.updated)
  ↓
Read ml.anomaly_score
  ↓
TEMPORARY anomaly-status branch        [src/integration/demo_branch.py]
     score >= 75  -> HIGH ANOMALY
     score <  75  -> NORMAL/MODERATE ANOMALY
  ↓
Demo output message
```

This branch produces an **"ML anomaly status"** label ONLY.
It is NOT a flood warning, NOT official flood risk, and NOT a final
classification. It exists purely to demonstrate viaSocket orchestration
until the rule engine is merged, and will be removed at integration.
Verified demo event: 2016-07-03 / PUNE_G004 / score 91.74 → HIGH ANOMALY
(delivered HTTP 200, all contract fields accessible).

## 1c. FUTURE FLOW (rule engine + hybrid — NOT built)

```
Webhook
  ↓
ML engine                    (frozen)
  ↓
Rule engine                  (teammate)
  ↓
Hybrid risk engine           (explicit weights TBD)
  ↓
Final risk score + risk level
  ↓
Preventive action / notification
```

## 2. Trigger

- Future: external weather/event trigger hitting a viaSocket webhook
  which invokes the Python risk service.
- Current (implemented): Python pushes one risk event to viaSocket via
  `send_risk_event(payload)` — ML-only flow.

## 3. Outgoing payload (IMPLEMENTED contract)

```json
{
  "event": "pune.flood_risk.updated",
  "date": "YYYY-MM-DD",
  "grid_id": "PUNE_G001|PUNE_G002|PUNE_G003|PUNE_G004",
  "ml":     { "anomaly_score": 0-100, "anomaly_percentile": 0-100 },
  "rule":   { "score": null, "risk_level": null, "recommended_actions": [] },
  "hybrid": { "final_risk_score": null, "risk_level": null },
  "metadata": {
    "source": "Pune FloodShield",
    "model": "IsolationForest",
    "model_version": "v1",
    "event_type": "RISK_EVENT | TEST_EVENT"
  }
}
```

Nulls in `rule`/`hybrid` are intentional placeholders — never invented.
Prototype payloads may carry an additive `demo` section (see §1b);
it is removed when the rule engine lands.

## 4. ML output feeding the payload

Sourced strictly from `src/risk/ml_adapter.get_ml_result(date, grid_id)`
(frozen IsolationForest artifact; higher = more anomalous; decision-support
only, not an official warning).

## 5. Future rule output (teammate)

Will fill `rule.score`, `rule.risk_level`, `rule.recommended_actions`
per `docs/RISK_ENGINE_CONTRACT.md` §4.

## 6. Future hybrid output

Will fill `hybrid.final_risk_score` and `hybrid.risk_level`
(weights TBD; `src/risk/hybrid_risk.py::combine` stays unimplemented
until then).

## 7. Error handling

`send_risk_event()` never raises for transport issues:
| Situation | Result |
| :--- | :--- |
| Webhook unset | `{"status":"skipped","reason":"webhook_not_configured"}` |
| Timeout | `{"status":"error","reason":"timeout"}` |
| Network/HTTP error | status dict with reason / http_status |
| 2xx | `{"status":"delivered","http_status":...}` |
Logs record only event name/date/grid and status codes — never URLs,
headers, or secrets.

## 8. Secret management

- Webhook URL read ONLY from env var `VIASOCKET_WEBHOOK_URL`.
- `.env.example` documents it; real `.env` is gitignored.
- No hardcoded endpoints anywhere in source.

## 9. Test procedure

```
python tests/test_viasocket_send.py
```
Builds ONE payload from the REAL frozen observation
(2016-07-03 / PUNE_G004 / score 91.74), marks it `TEST_EVENT`,
verifies the schema locally, and sends at most one request — only if
the webhook is configured. Without configuration it prints:
"viaSocket adapter ready; webhook configuration pending."

## 10. Future production workflow (NOT built yet)

```
External weather/event trigger
        ↓
viaSocket webhook
        ↓
Python risk service          (COMPUTATION)
        ↓
ML anomaly engine            (frozen)
        ↓
Rule engine                  (teammate)
        ↓
Hybrid risk engine           (weights TBD)
        ↓
viaSocket                    (AUTOMATION)
        ↓
Notification / logging / preventive action
```

Current implemented slice: **ML result → viaSocket** only.
