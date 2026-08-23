"""READ-ONLY ML accuracy check for the trained Module 1 XGBoost model.

Loads ONLY existing persisted artifacts. Never trains, fits, saves or
writes anything. Safe to run repeatedly.
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

MODEL_PATH = "outputs/vulnerability/xgboost_proxy_model.json"
CARD_PATH = "outputs/vulnerability/xgboost_proxy_model_card.json"
DATA_PATH = "outputs/vulnerability/proxy_training_grid.csv"
META_PATH = "outputs/vulnerability/proxy_training_grid_meta.json"
SHAP_JSON = "outputs/vulnerability/xgboost_zone_explanations.json"

LINE = "=" * 60


def pct(x):
    return f"{x * 100:.2f}%"


def main():
    import xgboost

    card = json.load(open(CARD_PATH))
    meta = json.load(open(META_PATH))
    data = pd.read_csv(DATA_PATH)
    features = meta["features"]
    target = "hydrologic_vulnerability_proxy"

    booster = xgboost.Booster()
    booster.load_model(MODEL_PATH)          # read-only load

    X = data[features]
    y = data[target]

    print(LINE)
    print("        FLOODSHIELD AI - ML MODEL VALIDATION")
    print(LINE)
    print()
    print("MODULE 1 - XGBOOST + SHAP")
    print()
    print("Model      : XGBClassifier (persisted Booster loaded read-only)")
    print(f"XGBoost    : {xgboost.__version__}")
    print(f"Features   : {len(features)}")
    print(f"Samples    : {len(data):,}")
    pos = int(y.sum())
    neg = int(len(y) - pos)
    print(f"Positive   : {pos:,}")
    print(f"Negative   : {neg:,}")

    # ---------------- EVALUATION 1: stratified random holdout -------------
    _, xb, _, yb = train_test_split(X, y, test_size=0.25,
                                    random_state=42, stratify=y)
    dm = xgboost.DMatrix(xb)
    pred = (booster.predict(dm) >= 0.5).astype(int)

    acc = accuracy_score(yb, pred)
    prec = precision_score(yb, pred, zero_division=0)
    rec = recall_score(yb, pred, zero_division=0)
    f1 = f1_score(yb, pred, zero_division=0)

    print()
    print("---------------- RANDOM HOLDOUT ----------------")
    print("[A] Persisted all-rows model re-scored on holdout")
    print("    (IN-SAMPLE BIAS: this model saw these rows during")
    print("     its final fit - figures are inflated)")
    print(f"Accuracy : {pct(acc)}")
    print(f"Precision: {pct(prec)}")
    print(f"Recall   : {pct(rec)}")
    print(f"F1 Score : {pct(f1)}")

    doc_a = card["evaluation"]["split_a"]
    print()
    print("[B] DOCUMENTED HOLDOUT (from model card):")
    print("     produced at training time by the model fitted")
    print("     on the 75% training portion only")
    print(f"Accuracy : {pct(doc_a['accuracy'])}")
    print(f"Precision: {pct(doc_a['precision'])}")
    print(f"Recall   : {pct(doc_a['recall'])}")
    print(f"F1 Score : {pct(doc_a['f1'])}")

    # ---------------- EVALUATION 2: spatial block -------------------------
    lon_available = "longitude" in data.columns
    if lon_available:
        lon_mid = float(data["longitude"].median())
        west = data["longitude"] <= lon_mid
        east_X = data.loc[~west, features]
        east_y = data.loc[~west, target]
        pred_e = (booster.predict(xgboost.DMatrix(east_X)) >= 0.5).astype(int)
        s_acc = accuracy_score(east_y, pred_e)
        s_prec = precision_score(east_y, pred_e, zero_division=0)
        s_rec = recall_score(east_y, pred_e, zero_division=0)
        s_f1 = f1_score(east_y, pred_e, zero_division=0)

        print()
        print("---------------- SPATIAL BLOCK -----------------")
        print("[A] Persisted all-rows model re-scored on East block")
        print(f"Accuracy : {pct(s_acc)}")
        print(f"F1 Score : {pct(s_f1)}")
        print(f"Precision: {pct(s_prec)}")
        print(f"Recall   : {pct(s_rec)}")

        doc_b = card["evaluation"]["split_b"]
        print()
        print("[B] DOCUMENTED SPATIAL BLOCK (from model card):")
        print("     West-trained model evaluated on East at training time")
        print(f"Accuracy : {pct(doc_b['accuracy'])}")
        print(f"F1 Score : {pct(doc_b['f1'])}")
        print(f"Precision: {pct(doc_b['precision'])}")
        print(f"Recall   : {pct(doc_b['recall'])}")
    else:
        print()
        print("Spatial evaluation unavailable from current persisted artifacts")

    # ---------------- SHAP (existing artifact) ----------------------------
    shap_data = json.load(open(SHAP_JSON)).get(
        "global_feature_importance_mean_abs_shap", {})
    ordered = sorted(shap_data.items(), key=lambda kv: -kv[1])

    print()
    print("---------------- SHAP --------------------------")
    print("Top Features (SHAP explanation, not accuracy):")
    for i, (name, val) in enumerate(ordered, start=1):
        print(f"{i}. {name}  (mean|shap|={val})")

    print()
    print("-" * LINE.__len__())
    print("Target type: hydrologic_vulnerability_proxy")
    print()
    print("NOTE:")
    print("These metrics measure agreement with the disclosed")
    print("rule-derived vulnerability proxy.")
    print("They are NOT verified historical flood prediction accuracy.")
    print(LINE)
    print("                    READ-ONLY CHECK COMPLETE")
    print(LINE)


if __name__ == "__main__":
    main()
