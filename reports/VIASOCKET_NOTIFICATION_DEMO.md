# VIASOCKET NOTIFICATION DEMO — ML-ONLY TEST REPORT

Date: 2026-08-22 · Scope: **ML risk output → ViaSocket → notification channel**
Mode: **HISTORICAL REPLAY / DEMO — NOT A LIVE FLOOD WARNING**

## 1. Event used

Real frozen replay observation, loaded via `get_live_risk` and
asserted against expected values before sending:
**2024-07-15 / PUNE_G004 / 79.22 HIGH / INCREASING**

## 2. Event payload fields (exact)

```json
{"event": "pune.flood_risk.updated",
 "date": "2024-07-15", "grid_id": "PUNE_G004",
 "risk_score": 79.22, "risk_level": "HIGH", "risk_trend": "INCREASING",
 "mode": "HISTORICAL_REPLAY", "demo": true,
 "message": "High zone risk detected during historical replay. Preventive action recommended.",
 "disclaimer": "HISTORICAL REPLAY / DEMO — NOT A LIVE FLOOD WARNING"}
```
No other ML values invented. `demo:true` + disclaimer present.

## 3. Webhook delivery status

| Item | Result |
| :--- | :--- |
| Attempted | YES — exactly **ONE** POST (existing transport reused) |
| HTTP status | **200 OK** |
| Client verdict | `delivered` |

## 4–7. Channel status

| Channel | Status | Actually verified? |
| :--- | :--- | :--- |
| Webhook acceptance | Delivered (HTTP 200) | Yes — response observed |
| Email | **NOT TESTED — connector unavailable on this side** | No. Rendering/sending executes inside the ViaSocket workflow; prepared template below is ready for that workflow |
| SMS | **NOT TESTED — connector unavailable** | No |
| WhatsApp | **NOT TESTED — connector unavailable** | No |

No success is claimed for any downstream channel — only webhook
acceptance (HTTP 200) is verified from this environment.

Prepared email template for the ViaSocket workflow:

> **Subject:** `[DEMO] HIGH ZONE RISK — PUNE_G004`
>
> PUNE FLOOD RESILIENCE DEMO
> Zone: PUNE_G004 · Date: 2024-07-15
> Risk Score: 79.22 · Risk Level: HIGH · Trend: INCREASING
> Recommended action: Preventive action recommended.
> HISTORICAL REPLAY / DEMO — NOT A LIVE FLOOD WARNING

Prepared short message (SMS/WhatsApp):

> `[DEMO] PUNE_G004 · Risk: HIGH (79.22) · Trend: INCREASING · Preventive action recommended. Historical replay — NOT a live flood warning.`

## 8. Connector limitations

No email/SMS/WhatsApp connectors are configured or observable in this
project; ViaSocket-side workflow execution (email rendering, channel
delivery) is outside our observability. Per instructions these channels
are reported honestly as NOT TESTED rather than assumed successful.

## 9. Replay confirmation

Payload carries `"mode": "HISTORICAL_REPLAY"`, `"demo": true`, and the
mandated disclaimer. The source observation was validated against the
frozen Module-2 table before send.

## 10. Production-safety confirmation

- NO production/live flood alert was generated — this was a single
  demo event flagged `demo:true`.
- One POST total; no retries, loops, or automation triggers.
- Webhook URL loaded from environment only; never printed/logged/stored.
- Modules 1–5, frozen dataset (`9886dee098f11f8f`) and architecture untouched.

Script: `tests/test_viasocket_notification_demo.py`.
