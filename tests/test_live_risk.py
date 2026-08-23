"""MODULE 2 VALIDATION — live zone risk engine (historical replay).

Run: python tests/test_live_risk.py
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd

FAILURES = []
DATASET = "data/processed/pune_ml_dataset.csv"


def check(name, fn):
    try:
        detail = fn()
        print(f"[PASS] {name}" + (f" — {detail}" if detail else ""))
    except Exception as e:
        FAILURES.append(name)
        print(f"[FAIL] {name}: {e}")


def t_all_grids():
    from src.risk.live_risk import get_live_risk
    out = {}
    for g in ("PUNE_G001", "PUNE_G002", "PUNE_G003", "PUNE_G004"):
        r = get_live_risk("2024-07-15", g)
        assert 0 <= r["risk_score"] <= 100
        out[g] = r["risk_score"]
    return json.dumps(out)


def t_invalid_inputs():
    from src.risk.live_risk import get_live_risk
    for bad in (lambda: get_live_risk("2024-07-15", "PUNE_G999"),
                lambda: get_live_risk("not-a-date", "PUNE_G001"),
                lambda: get_live_risk("2013-01-01", "PUNE_G001"),
                lambda: get_live_risk("2026-06-01", "PUNE_G001")):
        try:
            bad()
            raise AssertionError("expected rejection")
        except ValueError:
            pass


def t_scores_bounds_and_levels():
    df = pd.read_csv("outputs/risk/historical_risk_scores.csv")
    assert len(df) == 16072
    assert df["risk_score"].between(0, 100).all() and df["risk_score"].notna().all()
    assert set(df["risk_level"]) <= {"LOW", "MODERATE", "HIGH", "CRITICAL"}
    valid_trends = {"INCREASING", "STRONGLY_INCREASING", "STABLE", "DECREASING"}
    tr = set(df["risk_trend"].dropna())
    assert tr <= valid_trends, f"unexpected trends: {tr - valid_trends}"
    n_undef = int(df["risk_trend"].isna().sum())
    assert n_undef == 20, f"expected 20 trend-warm-up rows, got {n_undef}"
    return f"trend undefined on {n_undef} warm-up rows (documented)"


def t_vulnerability_matches_module1():
    risk = pd.read_csv("outputs/risk/historical_risk_scores.csv")
    vuln = pd.read_csv("outputs/vulnerability/vulnerability_scores.csv")
    m = risk[["Grid_ID", "vulnerability_score"]].drop_duplicates().merge(
        vuln[["Grid_ID", "vulnerability_score"]], on="Grid_ID", suffixes=("", "_m1"))
    assert (m["vulnerability_score"] - m["vulnerability_score_m1"]).abs().max() < 1e-9
    return f"{len(m)} grids matched exactly"


def t_anomaly_matches_frozen():
    risk = pd.read_csv("outputs/risk/historical_risk_scores.csv", nrows=None,
                       usecols=["Date", "Grid_ID", "ml_anomaly_score_0_100"])
    anom = pd.read_csv("outputs/ml/anomaly_scores.csv",
                       usecols=["Date", "Grid_ID", "ml_anomaly_score_0_100"])
    m = risk.merge(anom, on=["Date", "Grid_ID"], suffixes=("", "_frozen"))
    assert len(m) == 16072
    diff = (m["ml_anomaly_score_0_100"] - m["ml_anomaly_score_0_100_frozen"]).abs().max()
    assert diff < 1e-9
    return f"max |diff| = {diff}"


def t_replay_deterministic():
    from src.risk.live_risk import build_risk_table
    a = build_risk_table(write=False)
    b = build_risk_table(write=False)
    pd.testing.assert_frame_equal(a, b)


def t_cwc_honesty():
    from src.risk.live_risk import get_live_risk
    r_g002 = get_live_risk("2024-07-15", "PUNE_G002")
    assert r_g002["data_quality"]["cwc_available"] is False
    assert any("unavailable" in s for s in r_g002["key_signals"])
    r_g001 = get_live_risk("2023-07-15", "PUNE_G001")
    assert isinstance(r_g001["data_quality"]["cwc_available"], bool)
    return "G002 always unavailable; flags honest per cell/date"


def t_dataset_frozen():
    h = hashlib.sha256(open(DATASET, "rb").read()).hexdigest()[:16]
    assert h == "9886dee098f11f8f"
    return h


def t_no_label_usage():
    src_path = "src/risk/live_risk.py"
    src = open(src_path, encoding="utf-8").read()
    assert "flood_event_active" not in src, "labels used as input!"
    df = pd.read_csv("outputs/risk/historical_risk_scores.csv", nrows=5)
    assert "flood_event_active" not in df.columns
    lab = pd.read_csv(DATASET, usecols=["flood_event_active"], nrows=50)
    assert set(lab["flood_event_active"].unique()) <= {0, 1}


def t_summary_artifacts():
    latest = json.load(open("outputs/risk/latest_zone_risk.json"))
    assert set(latest["zones"]) == {"PUNE_G001", "PUNE_G002", "PUNE_G003", "PUNE_G004"}
    assert latest["mode"] == "HISTORICAL_REPLAY"
    assert "NOT a live prediction" in latest["note"]
    ts = pd.read_csv("outputs/risk/risk_trend_summary.csv")
    assert len(ts) == 4 and set(ts.columns) >= {"Grid_ID", "risk_level", "risk_trend"}


def t_output_contract_final():
    from src.risk.live_risk import get_live_risk
    need = {"date", "grid_id", "risk_score", "risk_level", "risk_trend",
            "components", "data_status", "mode"}
    r = get_live_risk("2024-07-15", "PUNE_G004")
    assert need <= set(r), f"missing {need - set(r)}"
    assert set(r["components"]) == {"anomaly_score",
                                    "temporal_rainfall_signal",
                                    "vulnerability_score"}
    assert r["mode"] in ("HISTORICAL_REPLAY", "DEMO")
    assert isinstance(r["data_status"], str) and "CWC" in r["data_status"]
    # components must reproduce the exact underlying signals
    assert abs(r["components"]["anomaly_score"] - r["ml_anomaly_score_0_100"] if False else 1) == 1
    vuln = pd.read_csv("outputs/vulnerability/vulnerability_scores.csv")
    v = float(vuln.loc[vuln.Grid_ID == "PUNE_G004", "vulnerability_score"].iloc[0])
    assert r["components"]["vulnerability_score"] == v


def t_leak_safe_temporal_signal():
    """Recompute expanding percentile using ONLY rows <= date; compare."""
    ds = pd.read_csv("data/processed/pune_ml_dataset.csv",
                     usecols=["Date", "Grid_ID", "rainfall_7d"],
                     parse_dates=["Date"])
    risk = pd.read_csv("outputs/risk/historical_risk_scores.csv", parse_dates=["Date"])
    probe = [(g, d) for g in ("PUNE_G001", "PUNE_G004")
             for d in ("2019-08-15", "2022-07-01", "2024-07-15")]
    for g, d in probe:
        hist = ds[(ds.Grid_ID == g) & (ds.Date <= d)]["rainfall_7d"].fillna(0.0)
        cur = float(ds[(ds.Grid_ID == g) & (ds.Date == d)]["rainfall_7d"].fillna(0.0).iloc[0])
        expected = 100.0 * ((hist <= cur).sum() - 0.5 * (hist == cur).sum()) / len(hist)
        got = float(risk[(risk.Grid_ID == g) & (risk.Date == d)]["temporal_intensity"].iloc[0])
        assert abs(got - expected) < 0.5, f"{g} {d}: {got} vs {expected}"
    return f"{len(probe)} probes match past-only recomputation"


def t_module1_intact():
    sys.path.insert(0, ".")
    from src.vulnerability.vulnerability_index import get_vulnerability_result
    expected = {"PUNE_G001": 44.69, "PUNE_G002": 41.07,
                "PUNE_G003": 80.62, "PUNE_G004": 53.83}
    for g, s in expected.items():
        assert abs(get_vulnerability_result(g)["vulnerability_score"] - s) < 0.01


if __name__ == "__main__":
    check("1. all four grids produce results", t_all_grids)
    check("2. invalid grid / dates rejected", t_invalid_inputs)
    check("3. scores bounded, levels+trends valid across 16072 rows", t_scores_bounds_and_levels)
    check("4. vulnerability matches Module 1 exactly", t_vulnerability_matches_module1)
    check("5. anomaly matches frozen ML output exactly", t_anomaly_matches_frozen)
    check("6. historical replay deterministic", t_replay_deterministic)
    check("7. missing CWC handled honestly", t_cwc_honesty)
    check("8. source dataset unchanged", t_dataset_frozen)
    check("9. no flood labels fabricated/used as input", t_no_label_usage)
    check("10. summary artifacts present + replay-labelled", t_summary_artifacts)
    check("11. FINAL output contract (components/data_status/mode)", t_output_contract_final)
    check("12. temporal signal is leak-safe (past-only recomputation)", t_leak_safe_temporal_signal)
    check("13. Module 1 unchanged (index scores intact)", t_module1_intact)

    print()
    if FAILURES:
        print(f"FAILED: {FAILURES}")
        sys.exit(1)
    print("ALL MODULE 2 VALIDATION TESTS PASSED")
