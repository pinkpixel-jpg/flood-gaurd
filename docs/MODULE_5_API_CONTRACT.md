# MODULE 5 — DELIVERY API CONTRACT (for frontend team)

Base: FastAPI app `src/delivery/api.py` · run with
`uvicorn src.delivery.api:app` · default role **PUBLIC**; elevated views via
header `X-Role: MNC` or `X-Role: DISASTER`.

## Endpoints

| Method | Path | Params | Notes |
| :--- | :--- | :--- | :--- |
| GET | `/api/health` | — | liveness + system/mode |
| GET | `/api/zones` | `date`, header X-Role | array of zone responses |
| GET | `/api/zones/{grid_id}` | `date`, `citizen_reports`, X-Role | normalized zone response |
| GET | `/api/risk/{grid_id}` | `date`, X-Role | risk block + public_alert |
| GET | `/api/vulnerability/{grid_id}` | — | index + xgboost-proxy scores |
| GET | `/api/prevention/{grid_id}` | `date`, `citizen_reports` | priority/actions/checklist/explanations |
| GET | `/api/environment/{grid_id}` | `date` | heat + water proxies, data_status |
| POST | `/api/reports` | JSON body | citizen report intake |
| GET | `/api/reports` | `grid_id`, `limit` | stored reports |
| GET | `/api/viasocket/event` | `grid_id`, `date` | automation event preview |

`grid_id` ∈ PUNE_G001..G004 · `date` within 2015-01-01..2025-12-31.

## Normalized zone response (MNC/DISASTER)

```json
{
  "date": "2024-07-15",
  "grid_id": "PUNE_G004",
  "zone_name": "North-East Pune",
  "vulnerability": {
    "score": 53.83, "level": "MODERATE",
    "explanations": ["low elevation (+15.0 pts)", "..."],
    "target_type": "transparent_vulnerability_index",
    "xgboost_proxy": {"score": 0.0,
                      "target_type": "hydrologic_vulnerability_proxy",
                      "note": "rule-distilled exposure estimate; NOT flood probability"}
  },
  "risk": {
    "score": 79.22, "level": "HIGH", "trend": "INCREASING",
    "mode": "HISTORICAL_REPLAY",
    "components": {"anomaly": 85.31, "temporal_rainfall": 91.25,
                   "vulnerability": 53.83},
    "disclaimer": "..."
  },
  "prevention": {"priority": "URGENT",
                 "recommended_actions": ["..."],
                 "checklist": ["..."],
                 "explanations": ["..."]},
  "environment": {
    "heat":  {"score": 96.52, "level": "HIGH",   "type": "EXPOSURE_PROXY"},
    "water": {"score": 12.3,  "level": "LOW",    "type": "WATER_DEFICIT_PROXY"}
  },
  "citizen_reports": {"count": 0},
  "routing": {"status": "UNAVAILABLE",
              "reason": "Complete road network unavailable"},
  "metadata": {"system": "Pune FloodShield", "mode": "HISTORICAL_REPLAY",
               "data_status": "IMD daily rainfall OK; CWC river level ..."}
}
```

Missing data is always `null` / `"UNAVAILABLE"` — never invented.
All scores are indicators/proxies; none is a flood probability.

## Role differences

| Field group | PUBLIC | MNC / DISASTER |
| :--- | :--- | :--- |
| date, grid_id, zone_name | ✓ | ✓ |
| risk score/level/trend | ✓ | ✓ |
| public_alert (plain-language) | ✓ | ✓ |
| citizen-reporting capability flag | ✓ | ✓ |
| routing status (+reason) | ✓ | ✓ |
| vulnerability scores + explanations + proxy model detail | ✗ | ✓ |
| prevention priority/actions/checklist/explanations | ✗ | ✓ |
| environment heat/water indicators | ✗ | ✓ |
| citizen_reports count | ✗ | ✓ |
| operational metadata/data_status | ✗ | ✓ |

## Citizen report

POST `/api/reports`
```json
{"grid_id": "PUNE_G004", "report_type": "WATERLOGGING|FLOODING|BLOCKED_DRAIN|OTHER",
 "description": "text", "timestamp": "ISO (optional)"}
→ 200 {"report_id": "CR-XXXXXXXXXXXX", "status": "SUBMITTED"}
```
400 on invalid grid/type/empty description. Reports stored verbatim in
`data/reports/citizen_reports.csv`.

## Safe route

Always today:
```json
{"status": "UNAVAILABLE", "reason": "Complete road network unavailable"}
```

## ViaSocket event

GET `/api/viasocket/event` returns
`{event:"pune.flood_risk.updated", date, grid_id, risk:{score,level,trend},
prevention:{priority,recommended_actions}, metadata:{source:"Pune FloodShield"}}`.
Transport stays with the existing `viasocket_client`; no secrets exposed
by any endpoint.
