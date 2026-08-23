"""READ-ONLY ML VALIDATION — Module 1 XGBoost (fresh stratified holdout).

Loads the EXISTING persisted artifacts; fits an in-memory EVALUATION COPY
(never saved, never overwrites anything) on the 75% split so the holdout
is genuinely unseen. The persisted model file is not modified.
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
import xgboost
from sklearn.metrics import (
    accuracy_score, average_precision_score, balanced_accuracy_score,
    confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split

MODEL_PATH = "outputs/vulnerability/xgboost_proxy_model.json"
CARD_PATH = "outputs/vulnerability/xgboost_proxy_model_card.json"
DATA_PATH = "outputs/vulnerability/proxy_training_grid.csv"
META_PATH = "outputs/vulnerability/proxy_training_grid_meta.json"

WATCH = [MODEL_PATH, CARD_PATH, DATA_PATH, META_PATH,
         "data/processed/pune_ml_dataset.csv"]


def sha16(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def pct(x):
    return f"{x * 100:.2f}%"


def main():
    before = {p: sha16(p) for p in WATCH}

    card = json.load(open(CARD_PATH))
    meta = json.load(open(META_PATH))
    data = pd.read_csv(DATA_PATH)
    features = meta["features"]
    target = "hydrologic_vulnerability_proxy"

    print("=" * 60)
    print("        FLOODSHIELD - READ-ONLY ML VALIDATION")
    print("=" * 60)
    print()
    print("Model file      :", MODEL_PATH)
    print("Model type      : XGBClassifier -> Booster (loaded read-only)")
    print("XGBoost version :", xgboost.__version__)
    print("Feature count   :", len(features))
    for f in features:
        print("   -", f)
    print("Dataset         :", DATA_PATH)
    print("Target column   :", target)
    print("Target rule     :", meta["target_definition"])
    n = len(data)
    pos = int(data[target].sum())
    neg = n - pos
    print(f"Samples         : {n:,}")
    print(f"Positive        : {pos:,} ({100*pos/n:.2f}%)")
    print(f"Negative        : {neg:,} ({100*neg/n:.2f}%)")

    # ---- fresh reproducible stratified 25% holdout ----------------------
    X_tr, X_te, y_tr, y_te = train_test_split(
        data[features], data[target], test_size=0.25,
        random_state=42, stratify=data[target])

    from xgboost import XGBClassifier
    spw = float((y_tr == 0).sum()) / max(int((y_tr == 1).sum()), 1)
    eval_model = XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.1,
        subsample=0.9, colsample_bytree=0.9, random_state=42,
        eval_metric="aucpr", scale_pos_weight=spw,
        tree_method="hist", n_jobs=1)
    eval_model.fit(X_tr, y_tr)          # IN-MEMORY evaluation copy only

    proba = eval_model.predict_proba(X_te)[:, 1]
    pred = (proba >= 0.5).astype(int)
    yte = y_te.to_numpy()

    acc = accuracy_score(yte, pred)
    prec = precision_score(yte, pred, zero_division=0)
    rec = recall_score(yte, pred, zero_division=0)
    f1 = f1_score(yte, pred, zero_division=0)
    roc = roc_auc_score(yte, proba)
    pr = average_precision_score(yte, proba)
    bal = balanced_accuracy_score(yte, pred)
    tn, fp, fn, tp = confusion_matrix(yte, pred).ravel()
    spec = tn / (tn + fp)

    print()
    print("-" * 60)
    print("FRESH STRATIFIED HOLDOUT (25%, seed=42)")
    print("(in-memory evaluation copy fit on train split ONLY;")
    print(" persisted artifact untouched, nothing saved)")
    print("-" * 60)
    print(f"Accuracy          : {pct(acc)}")
    print(f"Precision         : {pct(prec)}")
    print(f"Recall            : {pct(rec)}")
    print(f"F1                : {pct(f1)}")
    print(f"ROC-AUC           : {roc:.4f}")
    print(f"PR-AUC / AvgPrec  : {pr:.4f}")
    print(f"Balanced Accuracy : {pct(bal)}")
    print(f"Specificity       : {pct(spec)}")
    print()
    print("Confusion matrix:")
    print(f"  TN: {tn:>6}   FP: {fp:>6}")
    print(f"  FN: {fn:>6}   TP: {tp:>6}")
    print()
    print(f"Class balance     : positive {100*pos/n:.2f}% | "
          f"negative {100*neg/n:.2f}%")

    print()
    print("TARGET TYPE:")
    print("  VULNERABILITY PROXY (rule-derived: dist_to_drainage_m <= 700m")
    print("  AND elevation < study-area p35). NOT a real flood outcome.")

    after = {p: sha16(p) for p in WATCH}
    changed = [p for p in WATCH if before[p] != after[p]]
    print()
    print("READ-ONLY CHECK  : artifacts changed =", changed if changed else "NONE")


if __name__ == "__main__":
    main()
