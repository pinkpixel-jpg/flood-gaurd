"""MODULE 4 VALIDATION — heat exposure & water deficit proxies.

Run: python tests/test_heat_water.py
"""

import ast
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd

FAILURES = []
DATASET = "data/processed/pune_ml_dataset.csv"
DATASET_PATH = DATASET
GRIDS = {"PUNE_G001", "PUNE_G002", "PUNE_G003", "PUNE_G004"}


def check(name, fn):
    try:
        detail = fn()
        print(f"[PASS] {name}" + (f" — {detail}" if detail else ""))
    except Exception as e:
        FAILURES.append(name)
        print(f"[FAIL] {name}: {e}")


def t1_heat_valid():
    from src.risk.heat_water import get_environmental_risk
    r = get_environmental_risk("2024-05-15", "PUNE_G003")
    assert 0 <= r["heat"]["score"] <= 100
    assert r["heat"]["type"] == "EXPOSURE_PROXY"

    # hand-recompute min-max formula from frozen dataset
    df = pd.read_csv(DATASET_PATH, usecols=["Grid_ID", "built_up_pct", "vegetation_pct"])
    f = df.groupby("Grid_ID").first()
    mm = lambda s: (s - s.min()) / (s.max() - s.min()) * 100
    expected = round(0.6 * mm(f.built_up_pct)["PUNE_G003"]
                     + 0.4 * (100 - mm(f.vegetation_pct)["PUNE_G003"]), 2)
    assert abs(r["heat"]["score"] - expected) < 0.01
    return f"G003 heat={expected}"


def t2_water_valid():
    from src.risk.heat_water import get_environmental_risk
    r = get_environmental_risk("2024-03-01", "PUNE_G001")
    ds = pd.read_csv(DATASET_PATH, parse_dates=["Date"])
    row = ds[(ds.Grid_ID == "PUNE_G001") & (ds.Date == "2024-03-01")].iloc[0]
    exp30 = 30 * row.hist_mean_prior_years_mm
    ratio = float(np.clip(1 - row.rainfall_30d / exp30, 0, 1))
    assert abs(r["water"]["score"] - ratio * 100) < 0.01
    return f"score={r['water']['score']} (dry-season probe)"


def t3_bounds():
    df = pd.read_csv("outputs/risk/environmental_scores.csv")
    heat_ok = True  # heat checked separately below via compute_heat
    from src.risk.heat_water import compute_heat
    h = compute_heat()
    assert h["heat_score"].between(0, 100).all()
    w = df["water_score"].dropna()
    assert w.between(0, 100).all() and len(w) > 14000


def t4_levels():
    df = pd.read_csv("outputs/risk/environmental_scores.csv")
    assert set(df["water_level"].dropna()) <= {"LOW", "MODERATE", "HIGH"}
    from src.risk.heat_water import compute_heat
    h = compute_heat()
    assert set(h["heat_level"]) <= {"LOW", "MODERATE", "HIGH"}


def t5_deterministic():
    from src.risk.heat_water import build_water_table, compute_heat
    a = build_water_table(); b = build_water_table()
    pd.testing.assert_frame_equal(a, b)
    pd.testing.assert_frame_equal(compute_heat(), compute_heat())


def t6_missing_data_null_not_imputed():
    df = pd.read_csv("outputs/risk/environmental_scores.csv", parse_dates=["Date"])
    nulls = df[df["water_score"].isna()]
    assert len(nulls) == 1460, f"expected 1460 nulls (all-2015), got {len(nulls)}"
    assert nulls["Date"].dt.year.eq(2015).all()
    sample = json.loads(nulls.iloc[0]["water_explanations"])
    assert any("insufficient history" in s for s in sample)


def t7_telemetry_status():
    from src.risk.heat_water import get_environmental_risk, load_config
    cfg = load_config()["telemetry_status"]
    assert cfg == {"temperature_telemetry": "UNAVAILABLE",
                   "reservoir_storage_telemetry": "UNAVAILABLE"}
    r = get_environmental_risk("2024-05-15", "PUNE_G001")
    assert r["data_status"] == cfg


def t8_no_fabricated_temperature():
    df = pd.read_csv("outputs/risk/environmental_scores.csv", nrows=5)
    cols = [c.lower() for c in df.columns] + list(df.columns)
    assert not any("temp" in c for c in cols), "temperature-like column found!"
    src = open("src/risk/heat_water.py", encoding="utf-8").read()
    assert "read_csv" in src
    # engine reads ONLY the frozen dataset (declared usecols)
    usecols_line = [l for l in src.splitlines() if "usecols=" in l][0]
    for banned in ("temp", "storage", "reservoir"):
        assert banned not in usecols_line.lower()


def t9_no_fabricated_storage():
    df = pd.read_csv("outputs/risk/environmental_scores.csv", nrows=5)
    cols = list(df.columns)
    assert not any(("storage" in c.lower()) or ("reservoir" in c.lower()) for c in cols)


def t10_grid_date_handling():
    from src.risk.heat_water import get_environmental_risk
    for g in GRIDS:
        r = get_environmental_risk("2024-05-15", g)
        assert r["grid_id"] == g and 0 <= r["heat"]["score"] <= 100
    for bad in (lambda: get_environmental_risk("2024-05-15", "PUNE_G999"),
                lambda: get_environmental_risk("garbage", "PUNE_G001"),
                lambda: get_environmental_risk("2014-01-01", "PUNE_G001"),
                lambda: get_environmental_risk("2026-08-01", "PUNE_G001")):
        try:
            bad()
            raise AssertionError("accepted")
        except ValueError:
            pass


def t11_config_valid():
    cfg = json.load(open("src/risk/heat_water_config.json"))
    hw = sum(w["weight"] for w in cfg["heat"]["weights"].values())
    assert abs(hw - 1.0) < 1e-9
    for section in ("heat", "water"):
        bands = sorted((b["min"], b["max_exclusive"], name)
                       for name, b in cfg[section]["levels"].items())
        prev = 0
        for lo, hi, _ in bands:
            assert lo == prev, f"{section} bands overlap/gap at {lo}"
            prev = hi
        assert prev >= 100
    assert cfg["telemetry_status"]["temperature_telemetry"] == "UNAVAILABLE"


def t12_independence():
    tree = ast.parse(open("src/risk/heat_water.py", encoding="utf-8").read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    allowed = {"json", "logging", "os", "numpy", "pandas"}
    assert imported <= allowed, f"forbidden imports: {imported - allowed}"

    code = (
        "import sys; sys.path.insert(0,'.')\n"
        "from src.risk.heat_water import get_environmental_risk\n"
        "get_environmental_risk('2024-05-15','PUNE_G002')\n"
        "banned=[m for m in sys.modules if m.startswith(('src.ml','src.vulnerability',"
        "'sklearn','xgboost','shap','src.integration')) or m=='src.risk.live_risk' "
        "or m=='src.risk.rule_engine']\n"
        "assert not banned, banned\n"
        "print('CLEAN')\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert "CLEAN" in out.stdout, out.stderr[-300:]


if __name__ == "__main__":
    check("1. valid heat calculation (matches hand-computed formula)", t1_heat_valid)
    check("2. valid water-deficit calculation (dry-season probe)", t2_water_valid)
    check("3. score bounds respected (heat + water)", t3_bounds)
    check("4. level classification valid", t4_levels)
    check("5. deterministic output", t5_deterministic)
    check("6. missing data -> null with explanation (1460 rows, all 2015)", t6_missing_data_null_not_imputed)
    check("7. unavailable telemetry explicitly reported", t7_telemetry_status)
    check("8. no fabricated temperature columns/values", t8_no_fabricated_temperature)
    check("9. no fabricated storage/reservoir values", t9_no_fabricated_storage)
    check("10. correct grid/date handling + rejections", t10_grid_date_handling)
    check("11. configuration validity (weights=1.0, ordered bands)", t11_config_valid)
    check("12. independent of Modules 1-3 / ML / ViaSocket (AST+runtime)", t12_independence)

    print()
    if FAILURES:
        print(f"FAILED: {FAILURES}")
        sys.exit(1)
    print("ALL MODULE 4 TESTS PASSED")
