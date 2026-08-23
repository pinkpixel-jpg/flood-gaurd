import json
import logging
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from src.ml.feature_preparation import prepare

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

OUT_DIR = "outputs/ml"

MODEL_PARAMS = {
    "n_estimators": 300,
    "contamination": 0.01,
    "max_samples": "auto",
    "random_state": 42,
    "n_jobs": -1,
}


def train_isolation_forest(X_fit):
    model = IsolationForest(**MODEL_PARAMS)
    model.fit(X_fit)
    logger.info("IsolationForest fitted on %d rows x %d features", *X_fit.shape)
    return model


def score(model, X):
    raw = -model.decision_function(X)
    return np.asarray(raw, dtype=float)


def normalize_0_100(raw_all):
    order = raw_all.argsort().argsort()
    pct = 100.0 * order / (len(raw_all) - 1)
    return np.round(pct, 2)


def run():
    os.makedirs(OUT_DIR, exist_ok=True)
    df, feat, train_mask, eval_mask, fit_mask, meta = prepare()

    X_fit = feat.loc[fit_mask].to_numpy(dtype=float)
    model = train_isolation_forest(X_fit)

    raw = score(model, feat.to_numpy(dtype=float))
    norm = normalize_0_100(raw)

    out = df[["Date", "Grid_ID", "flood_event_active",
              "rainfall_1d", "rainfall_7d"]].copy()
    out["anomaly_score_raw"] = np.round(raw, 6)
    out["ml_anomaly_score_0_100"] = norm
    out["anomaly_percentile"] = norm.astype(int)
    out["period"] = np.where(eval_mask, "evaluation", "training")

    from scipy.stats import spearmanr
    rho_eval = float(spearmanr(raw[eval_mask.to_numpy()],
                               feat["rainfall_7d"].to_numpy()[eval_mask.to_numpy()]).statistic)
    direction_check = {
        "metric": "Spearman(anomaly_score_raw, rainfall_7d) on evaluation period",
        "value": rho_eval,
        "expected_sign": "positive (higher score = more anomalous)",
    }
    assert direction_check["value"] > 0.5, "score direction check failed"
    logger.info("direction check OK: %s = %.3f", direction_check["metric"], direction_check["value"])

    scores_path = os.path.join(OUT_DIR, "anomaly_scores.csv")
    out.to_csv(scores_path, index=False)
    logger.info("scores saved -> %s", scores_path)

    card = {
        **meta,
        "model": "sklearn.ensemble.IsolationForest",
        "params": MODEL_PARAMS,
        "preprocessing": "no scaling (tree-based); training-fit median imputation; availability indicators",
        "score_definition": "anomaly_score_raw = -(decision_function); higher = more anomalous",
        "normalization": "global percentile rank across all 16072 rows scaled to 0-100",
        "direction_check": direction_check,
        "train_event_exclusion": f"event days +/- {3} days removed from fit",
        "artifacts": {"scores": scores_path},
    }
    with open(os.path.join(OUT_DIR, "model_card.json"), "w") as f:
        json.dump(card, f, indent=2, default=str)
    logger.info("model card saved")

    return out, feat, df, card


if __name__ == "__main__":
    run()
