# VIASOCKET EMAIL DELIVERY TEST — PHASE 6B

Date: 2026-08-22 · Mode: **HISTORICAL REPLAY / DEMO — NOT A LIVE FLOOD WARNING**

## Test event

Real frozen replay observation (assert-guarded against the Module-2
table before sending):

```json
{"event": "pune.flood_risk.updated",
 "date": "2024-07-15", "grid_id": "PUNE_G004",
 "risk_score": 79.22, "risk_level": "HIGH", "risk_trend": "INCREASING",
 "mode": "HISTORICAL_REPLAY", "demo": true,
 "email_template": {"subject": "[DEMO] HIGH FLOOD RISK — PUNE_G004",
                    "body": ["FLOODGUARD AI — HISTORICAL REPLAY DEMO", "...",
                             "HISTORICAL REPLAY / DEMO", "NOT A LIVE FLOOD WARNING"]},
 "disclaimer": "HISTORICAL REPLAY / DEMO — NOT A LIVE FLOOD WARNING"}
```

Exactly **ONE** POST through the existing transport (`viasocket_client`).
No retries, no loops. Webhook URL from environment only; never printed.

## Results

| Check | Result |
| :--- | :--- |
| **Webhook** | **PASS — HTTP 200, `delivered`** |
| Timestamp (UTC) | 2026-08-22T09:20:43Z |
| **Email** | **NOT CONFIRMED RECEIVED** — webhook acceptance verified; actual inbox receipt must be confirmed by the human recipient. HTTP 200 proves ViaSocket accepted the event only. |

### Why the email is not marked RECEIVED

The send/delivery of the email happens inside the ViaSocket workflow,
which is outside this project's observability. Per test rules, success
is NOT claimed from HTTP 200 alone. Status will be upgraded to
RECEIVED only after explicit inbox confirmation by whoever received the
configured email action.

If no email arrived, the likely cause is on the ViaSocket side: the
email action's recipient/connector configuration in the workflow, not
the webhook delivery (which is proven working).

## Connector limitations

Email execution + credentials live entirely inside the ViaSocket
workflow configuration. SMS/WhatsApp remain untested/not configured.

## Safety confirmations

- Single HISTORICAL REPLAY / DEMO notification; `demo:true` present.
- No production/live flood alert generated.
- No secrets printed or stored; Modules 1–5, frozen dataset
  (`9886dee098f11f8f`) and architecture untouched.

Script: `tests/test_viasocket_email_demo.py`.
