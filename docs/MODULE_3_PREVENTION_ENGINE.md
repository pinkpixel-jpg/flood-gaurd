# MODULE 3 — PREVENTION ACTION ENGINE (FINAL)

Status: **COMPLETE** · Independent rule-based decision module ·
`rules_source = "rule_based"` · No ML anywhere.

## Purpose

"Given a risk situation, determine what preventive action should be
recommended." Answers WHAT SHOULD BE DONE — never whether flooding will
happen. All action wording uses "Recommend …" because the system does
not itself deploy pumps or notify agencies.

## Input / Output contract

Input (caller-supplied; Module-2 compatible field names):
```json
{"date":"YYYY-MM-DD","grid_id":"PUNE_G001..G004",
 "risk_score":0-100,
 "risk_level":"LOW|MODERATE|HIGH|CRITICAL",
 "risk_trend":"DECREASING|STABLE|INCREASING|STRONGLY_INCREASING|null",
 "vulnerability_level":"LOW|MODERATE|HIGH",
 "environmental_context":{},
 "citizen_reports":0}
```
Output:
```json
{"date","grid_id","risk_level","risk_trend","priority","recommended_actions":[],
 "triggered_rules":[{"rule_id","condition","action","explanation"}],
 "explanations":[],"rules_source":"rule_based"}
```

## Rule categories & thresholds (all in `src/risk/rule_config.json`, zero hidden thresholds)

| Category | Rules | Trigger |
| :--- | :--- | :--- |
| LOW | routine monitoring, no urgent intervention | risk_level = LOW |
| MODERATE | increased monitoring | level = MODERATE |
| MODERATE-rising | prepare response resources | MODERATE ∧ trend ∈ {INCREASING, STRONGLY_INCREASING} |
| HIGH (×4) | inspect drainage · deployment readiness · public advisory · vulnerable-area watch | level = HIGH |
| CRITICAL (×5) | immediate response activation · emergency resource deployment · notify disaster-management personnel · urgent public advisory · continuous monitoring until < CRITICAL | level = CRITICAL |
| Trend escalation | escalate preparedness | {HIGH, CRITICAL} ∧ trend rising |
| Trend step-down | standard cycle only as conditions improve | trend = DECREASING ∧ level ≠ CRITICAL |
| Citizen reports | field verification of reports (≥1) · cluster escalation (≥4) | `citizen_reports` |

## Priority ladder (documented)

`ROUTINE < ELEVATED < HIGH < URGENT`
base = LOW→ROUTINE, MODERATE→ELEVATED, HIGH→HIGH, CRITICAL→URGENT;
+1 step if trend INCREASING/STRONGLY_INCREASING; +1 if citizen_reports ≥ 4;
capped at URGENT. Examples: HIGH+STABLE→HIGH · HIGH+INCREASING→URGENT ·
CRITICAL+STRONGLY_INCREASING(+reports≥4)→URGENT.

## Citizen-report handling

Reports are contextual evidence only: ≥1 triggers a verification
recommendation; ≥4 triggers cluster-escalation. Reports are never
treated as confirmed flooding and never fabricated by the engine.

## Independence from ML (verified)

AST import scan: engine imports exactly `{datetime, json, os, pandas}`.
Runtime check: no Module-1/2/ML/ViaSocket modules loaded during use.
Consumes Module 2's output via plain dict fields (risk_score/risk_level/
risk_trend) — demonstrated in tests without importing live_risk inside
the engine.

## Reference implementation usage

Inspected `rule_based_reference/backend/models/action_engine.py` +
`config.py` (read-only). Adopted ideas: tier→priority mapping and the
capped citizen-report bonus concept. Rejected: their operational-claim
wording ("Deploy pumps", "Notify ward officers") replaced with
"Recommend …" phrasing. Runtime dependency on the reference: **none**
(hash + source-scan tests enforce this).

## Limitations

1. Rules encode prudent generic flood preparedness; they are not
   municipal SOPs and carry no official authority.
2. Thresholds are expert-set (documented), not calibrated against real
   incident outcomes (5 verified events).
3. citizen_reports is caller-supplied today; a live reporting pipeline
   arrives with Module 5.
4. English-only action text.

## Tests

`tests/test_rule_engine.py` → **15/15 PASS** (scenarios, escalations,
citizen handling, validation failures, traceability, determinism,
independence, reference integrity).
