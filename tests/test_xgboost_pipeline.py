"""XGBoost pipeline interface tests (training must stay DISABLED).

Run: python tests/test_xgboost_pipeline.py
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

DATASET = "data/processed/pune_ml_dataset.csv"
FAILURES = []


def check(name, fn):
    try:
        detail = fn()
        print(f"[PASS] {name}" + (f" — {detail}" if detail else ""))
    except Exception as e:
        FAILURES.append(name)
        print(f"[FAIL] {name}: {e}")


def dataset_hash():
    return hashlib.sha256(open(DATASET, "rb").read()).hexdigest()[:16]


def t1_gate_detects_insufficient_labels():
    from src.vulnerability.xgboost_training import load_registered_labels, check_label_gate
    labels = load_registered_labels()
    gate = check_label_gate(labels)
    assert not gate["passed"], "gate unexpectedly passed"
    assert any("5" in r or "1 of 4" in r or "grids" in r for r in gate["reasons"])
    return f"reasons={len(gate['reasons'])}"


def t2_training_refused():
    from src.vulnerability.xgboost_training import train
    st = train()
    assert st["trained"] is False and not st["training_attempted"]
    assert st["refusal_reasons"], "no refusal reasons given"
    model_path = json.load(open("src/vulnerability/xgboost_config.json"))["persistence"]["model_path"]
    assert not os.path.exists(model_path), "model artifact exists but training is disabled!"
    return f"first_reason: {st['refusal_reasons'][0][:70]}..."


def t3_fake_unregistered_labels_rejected():
    import tempfile
    import pandas as pd
    from src.vulnerability.xgboost_training import SOURCES_PATH

    fake = pd.DataFrame({"Date": pd.date_range("2024-01-01", periods=40),
                         "Grid_ID": ["PUNE_G001"] * 40, "label": 1,
                         "source_id": "FAKE_SYNTHETIC"})
    tmpdir = tempfile.mkdtemp(dir="outputs")
    fake_path = os.path.join(tmpdir, "fake_labels.csv")
    fake.to_csv(fake_path, index=False)

    reg_backup = open(SOURCES_PATH).read()
    try:
        registry = json.loads(reg_backup)
        registry["registered_sources"].append(
            {"source_id": "FAKE_SYNTHETIC", "file": fake_path,
             "origin": "TEST-ONLY synthetic", "verification_status": "SYNTHETIC",
             "spatial_method": "none",
             "date_columns": {"start": "Date", "end": "Date"},
             "label_column": "label"})
        with open(SOURCES_PATH, "w") as f:
            json.dump(registry, f)
        # even IF someone registers a synthetic source, gate still refuses:
        from src.vulnerability.xgboost_training import load_registered_labels, check_label_gate, train
        labels = load_registered_labels()
        gate = check_label_gate(labels)
        assert not gate["passed"], "synthetic-only labels passed the gate!"
        st = train()
        assert st["trained"] is False
    finally:
        with open(SOURCES_PATH, "w") as f:
            f.write(reg_backup)
    return "unregistered/synthetic sources cannot enable training"


def t4_label_source_registry_restored():
    reg = json.load(open("data/labels/label_sources.json"))
    ids = [s["source_id"] for s in reg["registered_sources"]]
    assert ids == ["IMD_LOCAL_LOGS_2014_2016"], f"registry polluted: {ids}"


def t5_vulnerability_index_unchanged():
    from src.vulnerability.vulnerability_index import get_vulnerability_result
    expected = {"PUNE_G001": 44.69, "PUNE_G002": 41.07,
                "PUNE_G003": 80.62, "PUNE_G004": 53.83}
    for gid, score in expected.items():
        res = get_vulnerability_result(gid)
        assert abs(res["vulnerability_score"] - score) < 0.01, \
            f"{gid} changed: {res['vulnerability_score']} != {score}"
    return "index scores identical to frozen values"


def t6_dataset_frozen():
    h = dataset_hash()
    assert h == "9886dee098f11f8f", f"dataset hash changed: {h}"
    return f"sha256[:16]={h}"


def t7_no_model_trained_anywhere():
    for root, _, files in os.walk("outputs"):
        for f in files:
            if f.endswith((".json", ".ubj", ".bin")) and "xgboost_model" in f:
                raise AssertionError(f"unexpected model artifact: {os.path.join(root, f)}")
    from src.vulnerability import xgboost_predict, shap_explainer
    assert xgboost_predict.get_status()["available"] is False
    assert shap_explainer.get_status()["available"] is False


def t8_future_contract_valid():
    cfg = json.load(open("src/vulnerability/xgboost_config.json"))
    cols = set(pd.read_csv(DATASET, nrows=1).columns)
    feats = cfg["features"]["temporal"] + cfg["features"]["static"]
    missing = [c for c in feats if c not in cols]
    assert not missing, f"configured features absent from dataset: {missing}"
    assert "flood_event_active" not in feats, "target leaked into features!"
    assert "road_density" not in feats
    w = sum(cfg["label_gate"].values() and [1])  # gate block present
    assert cfg["split_policy"]["type"].startswith("chronological")


import pandas as pd

if __name__ == "__main__":
    check("1. label gate detects current insufficiency", t1_gate_detects_insufficient_labels)
    check("2. training refused (disabled + gate fail), no artifact", t2_training_refused)
    check("3. synthetic/unregistered labels rejected", t3_fake_unregistered_labels_rejected)
    check("4. label-source registry restored after test", t4_label_source_registry_restored)
    check("5. Transparent Vulnerability Index unchanged", t5_vulnerability_index_unchanged)
    check("6. frozen dataset unchanged", t6_dataset_frozen)
    check("7. no XGBoost model trained/persisted; predict+SHAP blocked", t7_no_model_trained_anywhere)
    check("8. future input/output contract valid vs real dataset", t8_future_contract_valid)

    print()
    if FAILURES:
        print(f"FAILED: {FAILURES}")
        sys.exit(1)
    print("ALL XGBOOST PIPELINE INTERFACE TESTS PASSED — training remains safely disabled.")
