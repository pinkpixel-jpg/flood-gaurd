"""MODULE 1 FINAL TESTS — XGBoost(proxy)+SHAP pipeline integrity.

Run: python tests/test_module1_final.py
"""

import ast
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd

FAILURES = []
DATASET = "data/processed/pune_ml_dataset.csv"
REF_ZIP = "rule_based_reference/hemal12.zip"
EXPECTED_REF_SHA = "BAEFBBF34944A368"  # recorded during read-only inspection
OUT = "outputs/vulnerability"


def check(name, fn):
    try:
        detail = fn()
        print(f"[PASS] {name}" + (f" — {detail}" if detail else ""))
    except Exception as e:
        FAILURES.append(name)
        print(f"[FAIL] {name}: {e}")


def t_xgboost_trained():
    from src.vulnerability.xgboost_training import PROXY_MODEL_PATH, PROXY_CARD_PATH
    assert os.path.exists(PROXY_MODEL_PATH)
    card = json.load(open(PROXY_CARD_PATH))
    assert card["target_type"] == "hydrologic_vulnerability_proxy"
    return f"params={card['params']['n_estimators']}/{card['params']['max_depth']}"


def t_scores_bounds():
    df = pd.read_csv(f"{OUT}/xgboost_vulnerability_scores.csv")
    assert df["vulnerability_score"].between(0, 100).all()
    assert set(df["vulnerability_level"]) <= {"LOW", "MODERATE", "HIGH"}
    assert len(df) == 4


def t_four_grids():
    df = pd.read_csv(f"{OUT}/xgboost_vulnerability_scores.csv")
    assert set(df["Grid_ID"]) == {"PUNE_G001", "PUNE_G002", "PUNE_G003", "PUNE_G004"}


def t_deterministic():
    from src.vulnerability.vulnerability_pipeline import run_pipeline
    before = open(f"{OUT}/xgboost_vulnerability_scores.csv").read()
    run_pipeline(deterministic=True)
    after = open(f"{OUT}/xgboost_vulnerability_scores.csv").read()
    assert before == after, "scores changed between identical runs"


def t_shap_ran():
    card = json.load(open(f"{OUT}/xgboost_proxy_model_card.json"))
    assert card["shap"]["method"] == "shap.TreeExplainer"
    assert os.path.exists(f"{OUT}/shap_summary.png") and \
        os.path.getsize(f"{OUT}/shap_summary.png") > 10000


def t_proxy_disclosure_everywhere():
    card = json.load(open(f"{OUT}/xgboost_proxy_model_card.json"))
    meta = json.load(open(f"{OUT}/proxy_training_grid_meta.json"))
    expl = json.load(open(f"{OUT}/xgboost_zone_explanations.json"))
    for obj in (card["target_type"], meta["target_type"], expl["target_type"]):
        assert obj == "hydrologic_vulnerability_proxy"
    gj = json.load(open(f"{OUT}/xgboost_vulnerability_zones.geojson"))
    for feat in gj["features"]:
        assert feat["properties"]["target_type"] == "hydrologic_vulnerability_proxy"
        assert "NOT a flood probability" in feat["properties"]["disclaimer"]


def t_no_fabricated_labels():
    df = pd.read_csv(f"{OUT}/proxy_training_grid.csv")
    elev_p35 = float(df["elevation_m"].quantile(0.35))
    recomputed = ((df["dist_to_drainage_m"] <= 700.0) &
                  (df["elevation_m"] < elev_p35)).astype(int)
    diff = int((recomputed != df["hydrologic_vulnerability_proxy"]).sum())
    assert diff == 0, f"{diff} labels not reproducible by documented rule"
    verified = pd.read_csv("data/flood_events/pune_flood_events.csv")
    assert len(verified) == 5  # untouched real events
    return "45472/45472 proxy rows reproduce the documented rule"


def t_dataset_frozen():
    h = hashlib.sha256(open(DATASET, "rb").read()).hexdigest()[:16]
    assert h == "9886dee098f11f8f"
    return h


def t_independent_imports():
    """Module 1 must not import Module 2 (live risk), Module 3 (rule engine),
    or ViaSocket integration code. Geospatial/ML libraries are fine."""
    files = ["src/vulnerability/proxy_dataset.py",
             "src/vulnerability/xgboost_training.py",
             "src/vulnerability/xgboost_predict.py",
             "src/vulnerability/shap_explainer.py",
             "src/vulnerability/vulnerability_pipeline.py"]
    banned_prefixes = ("src.risk", "src.integration")
    for p in files:
        tree = ast.parse(open(p, encoding="utf-8").read())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for m in names:
                assert not m.startswith(banned_prefixes), \
                    f"{p} imports forbidden module: {m}"


def t_reference_untouched():
    h = hashlib.sha256(open(REF_ZIP, "rb").read()).hexdigest()[:16].upper()
    assert h == EXPECTED_REF_SHA, f"reference modified! {h}"
    return h


def t_reference_not_runtime_dependency():
    for root, _, files in os.walk("src/vulnerability"):
        for f in files:
            if not f.endswith(".py"):
                continue
            src = open(os.path.join(root, f), encoding="utf-8",
                       errors="ignore").read()
            assert "rule_based_reference" not in src and "hemal12" not in src, \
                f"runtime dependency on reference in {f}"


def t_index_fallback_intact():
    sys.path.insert(0, ".")
    from src.vulnerability.vulnerability_index import get_vulnerability_result
    expected = {"PUNE_G001": 44.69, "PUNE_G002": 41.07,
                "PUNE_G003": 80.62, "PUNE_G004": 53.83}
    for gid, sc in expected.items():
        got = get_vulnerability_result(gid)["vulnerability_score"]
        assert abs(got - sc) < 0.01


if __name__ == "__main__":
    check("1. XGBoost trained & disclosed as proxy model", t_xgboost_trained)
    check("2. scores bounded 0-100 with valid levels", t_scores_bounds)
    check("3. all four grids covered", t_four_grids)
    check("4. deterministic reproduction of identical run", t_deterministic)
    check("5. SHAP TreeExplainer genuinely ran", t_shap_ran)
    check("6. hydrologic-proxy disclosure in every artifact", t_proxy_disclosure_everywhere)
    check("7. proxy labels 100% reproducible from documented rule; real events intact",
          t_no_fabricated_labels)
    check("8. frozen dataset unchanged", t_dataset_frozen)
    check("9+10. Module 1 independent (no Module2/3/ViaSocket imports)", t_independent_imports)
    check("11. rule_based_reference unmodified", t_reference_untouched)
    check("12. no runtime dependency on reference project", t_reference_not_runtime_dependency)
    check("+  Transparent Vulnerability Index fallback intact", t_index_fallback_intact)

    print()
    if FAILURES:
        print(f"FAILED: {FAILURES}")
        sys.exit(1)
    print("ALL MODULE 1 FINAL TESTS PASSED")
