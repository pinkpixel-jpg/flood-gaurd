# MODULE 5 — DELIVERY LAYER ARCHITECTURE (design only)

Status: **ARCHITECTURE PHASE.** Dashboard, SMS/WhatsApp, safe routes and
citizen reporting are NOT built yet. ViaSocket connectivity already
works and is untouched.

## Common data backbone

All interfaces consume the same contract JSONs:
ML anomaly result (`ml_adapter`), vulnerability index (Module 1),
risk+actions (Module 3), heat/water scores (Module 4).

## A. MNC / Business interface

Needs: site→grid mapping, current risk_level + trend per site,
travel-disruption flags (later: road data), asset exposure counts,
recommended_actions, 7-day history sparklines.
Focus: business continuity & employee safety decisions.

## B. Public / Citizen interface

Needs: simplified colour status per locality (LOW→CRITICAL), "what this
means" plain-language text from Module 3 actions, safe-route entry point
(future), citizen-report form (future), explicit
decision-support disclaimer.
Focus: simplicity + trust.

## C. Disaster Management interface

Needs: city-wide map (4 grids today, ward-level later), high-risk zone
ranking, risk trend arrows, top SHAP/weight factors per zone, citizen
reports overlay (future), operational recommendation feed.
Focus: prioritisation & response.

## D. ViaSocket automation (LIVE component)

Already working: ML result → webhook → ML anomaly-status demo workflow.
Future workflows documented in VIA_SOCKET_INTEGRATION.md:
weather/event trigger → risk computation → recommendation → notification.

Delivery channels via viaSocket flows: dashboard push, e-mail/SMS/
WhatsApp gateways, emergency-team workflow hooks, audit logging.
Python computes; viaSocket only orchestrates.

## Staged build order

1. Single-page dashboard reading existing JSONs (fastest demo value)
2. Role-based views (MNC/Public/Disaster) over the same API payloads
3. Notification channels via viaSocket templates
4. Citizen reporting intake → validation queue (schema below)
5. Safe-route service (blocked until road network exists — see
   FUTURE_CITIZEN_AND_ROUTE.md)
