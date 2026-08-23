"""RULE ENGINE — Module 3: INDEPENDENT PREVENTION ACTION RECOMMENDATION.

A rule-based DECISION module. It answers "WHAT SHOULD BE DONE given a
risk situation?" — it never predicts whether flooding will happen.

INDEPENDENCE CONTRACT (enforced by tests):
- imports NOTHING from the ML modules, vulnerability modules, the
  temporal risk engine, Isolation Forest, XGBoost, SHAP, or ViaSocket
- runs from a caller-supplied risk-context object alone

Rule configuration:
- PRODUCTION rules:  src/risk/rule_config.json   (EMPTY today — the
  teammate inserts reviewed rules; engine then honestly returns zero
  recommendations rather than inventing actions)
- DEMO rules:        src/risk/rule_config_demo.json (flagged
  DEMO_ONLY_NOT_PRODUCTION; used only by the scenario test framework)

Rule schema (insert into config["rules"]):
{
  "rule_id": "...",
  "description": "...",
  "condition": {"all": [{"field": "risk_score", "op": ">=", "value": 60},
                        {"field": "environmental_context.rainfall_1d",
                         "op": ">=", "value": 75}]},
  "action": "recommended action text",
  "explanation": "why this action"
}
Supported ops: ==, !=, >=, <=, >, <, in, not_in.
Dotted field paths reach nested context keys; missing fields make the
predicate False and are reported as skipped_with_missing_field.
"""

import json
import os
from datetime import date as _date, datetime

import pandas as pd

VALID_GRID_IDS = ("PUNE_G001", "PUNE_G002", "PUNE_G003", "PUNE_G004")
VALID_RISK_LEVELS = ("LOW", "MODERATE", "HIGH", "CRITICAL")
VALID_TRENDS = ("DECREASING", "STABLE", "INCREASING", "STRONGLY_INCREASING")

RULE_RESULT_FIELDS = {"date", "grid_id", "rule_score", "risk_level",
                      "recommended_actions"}

_DIR = os.path.dirname(__file__)
PRODUCTION_CONFIG = os.path.join(_DIR, "rule_config.json")
DEMO_CONFIG = os.path.join(_DIR, "rule_config_demo.json")


# ---------------------------------------------------------------- input side

def normalize_date(value):
    """Accept ISO strings / date / datetime / Timestamp -> 'YYYY-MM-DD'."""
    if isinstance(value, str):
        try:
            ts = pd.Timestamp(value)
        except Exception as e:
            raise ValueError(f"unparseable date {value!r}") from e
    elif isinstance(value, (_date, datetime, pd.Timestamp)):
        ts = pd.Timestamp(value)
    else:
        raise ValueError(f"unsupported date type {type(value).__name__}")
    return ts.normalize().strftime("%Y-%m-%d")


def validate_rule_input(date, grid_id):
    """Validate a rule-engine query input. Independent of ML."""
    if grid_id not in VALID_GRID_IDS:
        raise ValueError(f"unknown grid_id {grid_id!r}; expected one of {VALID_GRID_IDS}")
    return normalize_date(date), grid_id


def validate_rule_output(result):
    """Validate a rule-engine OUTPUT against the interface contract."""
    missing = RULE_RESULT_FIELDS - set(result or {})
    if missing:
        raise ValueError(f"invalid rule result; missing fields: {sorted(missing)}")

    if result["date"] != normalize_date(result["date"]):
        raise ValueError("date must be normalized 'YYYY-MM-DD'")
    if result["grid_id"] not in VALID_GRID_IDS:
        raise ValueError(f"invalid grid_id {result['grid_id']!r}")

    s = result["rule_score"]
    if not isinstance(s, (int, float)) or not (0 <= float(s) <= 100):
        raise ValueError(f"rule_score must be numeric 0-100, got {s!r}")

    if result["risk_level"] not in VALID_RISK_LEVELS:
        raise ValueError(f"risk_level must be one of {VALID_RISK_LEVELS}, "
                         f"got {result['risk_level']!r}")

    actions = result["recommended_actions"]
    if not isinstance(actions, list) or not all(isinstance(a, str) for a in actions):
        raise ValueError("recommended_actions must be a list of strings")
    return True


# ------------------------------------------------------- prevention engine

def load_rules(config_path=None, use_demo=False):
    path = config_path or (DEMO_CONFIG if use_demo else PRODUCTION_CONFIG)
    with open(path) as f:
        cfg = json.load(f)
    rules = cfg.get("rules", [])
    for r in rules:
        _validate_rule_def(r)
    return rules, cfg


def _validate_rule_def(r):
    required = {"rule_id", "condition", "action", "explanation"}
    missing = required - set(r or {})
    if missing:
        raise ValueError(f"malformed rule {r!r}: missing {sorted(missing)}")
    if not isinstance(r["condition"], dict) or not r["condition"]:
        raise ValueError(f"rule {r['rule_id']}: condition must be a non-empty dict")


def _resolve_field(context, dotted):
    node = context
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None, False
        node = node[part]
    return node, True


_OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">=": lambda a, b: a is not None and a >= b,
    "<=": lambda a, b: a is not None and a <= b,
    ">": lambda a, b: a is not None and a > b,
    "<": lambda a, b: a is not None and a < b,
    "in": lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
}


def _eval_predicate(context, p, skipped):
    value, present = _resolve_field(context, p["field"])
    op = _OPS[p["op"]]
    ok = present and op(value, p["value"])
    rendered = f"{p['field']} {p['op']} {p['value']!r}"
    if not present:
        skipped.append(p["field"])
    return bool(ok), rendered


def _eval_condition(context, cond):
    skipped = []
    parts = []
    if "all" in cond:
        results = [_eval_predicate(context, p, skipped) for p in cond["all"]]
        passed = all(ok for ok, _ in results)
        parts = [txt for _, txt in results]
    elif "any" in cond:
        results = [_eval_predicate(context, p, skipped) for p in cond["any"]]
        passed = any(ok for ok, _ in results)
        parts = [txt for _, txt in results]
    else:
        ok, txt = _eval_predicate(context, cond, skipped)
        passed = ok
        parts = [txt]
    return passed, " AND ".join(parts), sorted(set(skipped))


def evaluate_prevention(context, rules=None, use_demo=False):
    """Evaluate prevention rules against one risk-context object.

    context (caller-supplied; example shape, NOT production data):
      {"date","grid_id","risk_score","risk_level","risk_trend",
       "vulnerability_level", "environmental_context": {...},
       "citizen_reports": 0}

    Returns the output contract:
      {date, grid_id, risk_level, risk_trend, priority,
       recommended_actions[], triggered_rules[], explanations[],
       rules_source}
    """
    required = ("date", "grid_id", "risk_score", "risk_level")
    missing = [k for k in required if k not in (context or {})]
    if missing:
        raise ValueError(f"context missing required fields: {missing}")

    d = normalize_date(context["date"])
    gid = context["grid_id"]
    if gid not in VALID_GRID_IDS:
        raise ValueError(f"unknown grid_id {gid!r}")
    if context["risk_level"] not in VALID_RISK_LEVELS:
        raise ValueError(f"invalid risk_level {context['risk_level']!r}; "
                         f"expected one of {VALID_RISK_LEVELS}")
    trend = context.get("risk_trend")
    if trend is not None and trend not in VALID_TRENDS:
        raise ValueError(f"invalid risk_trend {trend!r}; "
                         f"expected one of {VALID_TRENDS} or null")
    score = context["risk_score"]
    if not isinstance(score, (int, float)) or not 0 <= float(score) <= 100:
        raise ValueError("risk_score must be numeric 0-100")

    reports = context.get("citizen_reports", 0)
    if not isinstance(reports, int) or reports < 0:
        raise ValueError("citizen_reports must be a non-negative integer")

    if rules is None:
        rules, cfg = load_rules(use_demo=use_demo)
    else:
        for r in rules:
            _validate_rule_def(r)
        cfg = {}

    recommended = []
    triggered = []
    explanations = []
    all_skipped = []
    for r in rules:
        passed, cond_text, skipped = _eval_condition(context, r["condition"])
        if skipped:
            all_skipped.extend(f"{r['rule_id']}:{s}" for s in skipped)
        if passed:
            recommended.append(r["action"])
            triggered.append({
                "rule_id": r["rule_id"],
                "condition": f"IF {cond_text}",
                "action": r["action"],
                "explanation": r["explanation"],
            })
            explanations.append(f"{r['rule_id']}: {cond_text} -> {r['explanation']}")

    out = {
        "date": d,
        "grid_id": gid,
        "risk_level": context["risk_level"],
        "risk_trend": trend,
        "priority": _compute_priority(cfg, context, trend, reports),
        "recommended_actions": recommended,
        "triggered_rules": triggered,
        "explanations": explanations,
        "rules_source": cfg.get("rules_source", "rule_based"),
    }
    if not rules:
        out["note"] = ("No production rules registered yet "
                       "(rule_config.json.rules is empty); zero recommendations returned.")
    if all_skipped:
        out["skipped_predicates_missing_fields"] = sorted(set(all_skipped))
    return out


def _compute_priority(cfg, context, trend, reports):
    """Documented ladder: base(level) + trend steps + citizen-report steps."""
    p = cfg.get("priority") or {}
    order = p.get("order", ["ROUTINE", "ELEVATED", "HIGH", "URGENT"])
    base = p.get("base_by_level", {}).get(context["risk_level"], "ROUTINE")
    rank = order.index(base) if base in order else 0
    rank += int(p.get("trend_bonus_steps", {}).get(str(trend), 0))
    thr = p.get("citizen_report_threshold", 4)
    if reports is not None and reports >= thr:
        rank += int(p.get("citizen_report_bonus_steps", 1))
    return order[min(rank, len(order) - 1)]
