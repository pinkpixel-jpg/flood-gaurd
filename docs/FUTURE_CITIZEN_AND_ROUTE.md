# FUTURE: SAFE ROUTE + CITIZEN REPORTING (design & data requirements only)

Status: **NOT IMPLEMENTED.** No fake road data, no fake reports.

## A. Safe Route Suggestion

### Blocking dependency (honest)

> Complete Pune road network is UNAVAILABLE in this project
> (Overpass outage; only a central-Pune-only graphml exists, which we
> refuse to present as full coverage). Safe routing is BLOCKED until
> real road data is acquired.

### Minimum data required

1. **Road network** covering the full study area with geometry +
   class tags — sources: retry Overpass in a quiet window, BBBike/Geofabrik
   regional extract, or municipal GIS export
2. **Risk-affected segment mapping:** join grid/zone risk polygons to
   road segments (spatial intersection), producing per-segment risk flags
3. **Routing engine:** OSRM / Valhalla / networkx on the local graph,
   with risk-weighted edge costs (`cost = length × (1 + w·risk_flag)`)
4. Flood-prone segment history for calibration (real records only)

### Output contract (future)

```json
{
  "from": "lat,lon", "to": "lat,lon",
  "route": "geometry",
  "risk_flags_on_route": ["PUNE_G004 HIGH"],
  "alternative_recommended": true
}
```

## B. Citizen-Source Reporting

### Minimum viable schema

```json
{
  "report_id": "uuid",
  "timestamp": "ISO-8601",
  "location": {"lat": 0.0, "lon": 0.0},
  "grid_id": "auto-assigned from lat/lon",
  "report_type": "WATERLOGGING|DRAIN_OVERFLOW|TREE_FALL|HEAT_ISSUE|OTHER",
  "severity": "LOW|MODERATE|HIGH",
  "description": "free text",
  "image_url": null,
  "status": "SUBMITTED|VERIFIED|REJECTED"
}
```

### Pipeline design

Intake (dashboard/API form) → auto-grid assignment → validation queue
(dedupe, spam filter, optional photo) → VERIFIED reports may be used as
**future real labels** for Module 1 XGBoost (this is the honest path to
supervised learning!) and displayed on Disaster-Management map.

Storage: append-only CSV/SQLite during hackathon; proper DB later.
