import json
import logging
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.ml.anomaly_model import run, OUT_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PLOTS_DIR = os.path.join(OUT_DIR, "plots")
GRIDS = ["PUNE_G001", "PUNE_G002", "PUNE_G003", "PUNE_G004"]

report_lines = []


def rep(s=""):
    print(s)
    report_lines.append(str(s))


def percentile_of(values):
    order = values.argsort().argsort()
    return 100.0 * order / (len(values) - 1)


def event_replay(scores):
    rep("=" * 70)
    rep("HISTORICAL EVENT REPLAY (5 verified event-days; unsupervised model)")
    rep("Model never used flood labels; event days were EXCLUDED from fit.")
    rep("=" * 70)

    ev = scores[scores["flood_event_active"] == 1].copy()
    ev["rank_global"] = scores["anomaly_score_raw"].rank(ascending=False).astype(int).loc[ev.index]
    ev["rank_in_grid"] = (scores.groupby("Grid_ID")["anomaly_score_raw"]
                          .rank(ascending=False).astype(int).loc[ev.index])
    ev["top1pct"] = ev["anomaly_percentile"] >= 99
    ev["top5pct"] = ev["anomaly_percentile"] >= 95
    ev["top10pct"] = ev["anomaly_percentile"] >= 90

    base_raw = scores["rainfall_7d"].to_numpy()
    scores["baseline_rainfall_percentile"] = np.round(percentile_of(base_raw), 2)
    bmap = scores.set_index(["Date", "Grid_ID"])["baseline_rainfall_percentile"]
    ev["baseline_rainfall7d_percentile"] = [
        bmap.get((d, g)) for d, g in zip(ev["Date"], ev["Grid_ID"])]
    ev["baseline_rank_global"] = pd.Series(
        (-base_raw).argsort().argsort() + 1, index=scores.index)[ev.index]

    cols = ["Date", "Grid_ID", "ml_anomaly_score_0_100", "anomaly_percentile",
            "rank_global", "rank_in_grid", "top1pct", "top5pct", "top10pct",
            "baseline_rainfall7d_percentile", "baseline_rank_global"]
    ev_out = ev[cols].sort_values("Date")
    rep(ev_out.to_string(index=False))

    hits = {k: int(ev[k].sum()) for k in ("top1pct", "top5pct", "top10pct")}
    rep("")
    rep(f"event-days flagged: top1%={hits['top1pct']}/5  top5%={hits['top5pct']}/5  "
        f"top10%={hits['top10pct']}/5")

    rho = float(pd.Series(scores["anomaly_score_raw"]).corr(
        scores["rainfall_7d"], method="spearman"))
    rho_ev = float(ev["ml_anomaly_score_0_100"].corr(
        ev["baseline_rainfall7d_percentile"], method="spearman"))
    rep(f"Spearman(IF score, rainfall_7d) full record : {rho:.3f}")
    rep(f"Spearman(IF vs baseline) on 5 event-days    : {rho_ev:.3f}")
    rep("")
    rep("NOTE: n=5 event-days -> NO statistically meaningful accuracy metrics are")
    rep("possible or claimed. This is qualitative replay evidence only.")

    ev_out.to_csv(os.path.join(OUT_DIR, "event_replay.csv"), index=False)
    return ev_out, {"spearman_if_vs_rainfall7d": rho,
                    "spearman_if_vs_baseline_on_events": rho_ev,
                    "flag_counts": hits}


def grid_analysis(scores):
    rep("")
    rep("=" * 70)
    rep("PER-GRID ANALYSIS")
    rep("=" * 70)
    rows = []
    for gid in GRIDS:
        s = scores[scores["Grid_ID"] == gid]
        top_dates = (s.sort_values("ml_anomaly_score_0_100", ascending=False)
                       .head(3)[["Date", "ml_anomaly_score_0_100"]]
                       .values.tolist())
        rows.append({
            "grid_id": gid,
            "n_rows": len(s),
            "score_mean": round(s["ml_anomaly_score_0_100"].mean(), 2),
            "score_p95": round(s["ml_anomaly_score_0_100"].quantile(0.95), 2),
            "score_max": round(s["ml_anomaly_score_0_100"].max(), 2),
            "days_in_global_top1pct": int((s["anomaly_percentile"] >= 99).sum()),
            "top3_most_anomalous_dates": "; ".join(
                f"{pd.Timestamp(d).date()} ({v:.0f})" for d, v in top_dates),
        })
    gs = pd.DataFrame(rows)
    rep(gs.to_string(index=False))
    gs.to_csv(os.path.join(OUT_DIR, "grid_summary.csv"), index=False)

    rep("")
    rep("SAME-DATE CROSS-GRID SPREAD on each grid's most anomalous day")
    rep("(hyperlocal concept: identical regional weather -> different scores):")
    for gid in GRIDS:
        s = scores[scores["Grid_ID"] == gid]
        dmax = s.loc[s["ml_anomaly_score_0_100"].idxmax(), "Date"]
        same = scores[scores["Date"] == dmax][["Grid_ID", "ml_anomaly_score_0_100", "rainfall_1d"]]
        rep(f"  {pd.Timestamp(dmax).date()} (triggered by {gid}):")
        for _, r in same.iterrows():
            rep(f"     {r['Grid_ID']}  score={r['ml_anomaly_score_0_100']:6.2f}  rain1d={r['rainfall_1d']:6.2f}mm")


def make_plots(scores, df):
    os.makedirs(PLOTS_DIR, exist_ok=True)
    sc = scores.copy()

    fig, ax = plt.subplots(figsize=(13, 4))
    for gid in GRIDS:
        s = sc[sc["Grid_ID"] == gid].sort_values("Date")
        ax.plot(s["Date"], s["ml_anomaly_score_0_100"], lw=0.6, alpha=0.6, label=gid)
    ev = sc[sc["flood_event_active"] == 1]
    ax.scatter(ev["Date"], ev["ml_anomaly_score_0_100"], color="red", zorder=5,
               marker="v", s=60, label="verified flood event-day")
    ax.axvline(pd.Timestamp("2024-01-01"), color="grey", ls="--", lw=1)
    ax.text(pd.Timestamp("2024-02-01"), 98, "evaluation period →", fontsize=8, color="grey")
    ax.set_ylabel("ml_anomaly_score_0_100")
    ax.set_title("ML anomaly score over time (higher = more anomalous)")
    ax.legend(ncol=5, fontsize=8)
    ax.set_ylim(-2, 104)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, "1_anomaly_over_time.png"), dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 5.5))
    for gid in GRIDS:
        s = sc[sc["Grid_ID"] == gid]
        ax.scatter(s["rainfall_7d"], s["ml_anomaly_score_0_100"], s=3, alpha=0.35, label=gid)
    ax.set_xlabel("rainfall_7d accumulation (mm)")
    ax.set_ylabel("ml_anomaly_score_0_100")
    ax.set_title("Rainfall accumulation vs ML anomaly score")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, "2_rainfall_vs_anomaly.png"), dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.hist(sc["ml_anomaly_score_0_100"], bins=60, color="#4477aa")
    evp = sc.loc[sc["flood_event_active"] == 1, "ml_anomaly_score_0_100"]
    for v in evp:
        ax.axvline(v, color="red", ls="--", lw=1)
    ax.set_xlabel("ml_anomaly_score_0_100")
    ax.set_ylabel("rows")
    ax.set_title("Score distribution (red dashed = verified event-days)")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, "3_score_distribution.png"), dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    data = [sc.loc[sc["Grid_ID"] == g, "ml_anomaly_score_0_100"] for g in GRIDS]
    ax.boxplot(data, tick_labels=GRIDS, showfliers=False)
    evg = sc[sc["flood_event_active"] == 1]
    ax.scatter(evg["Grid_ID"], evg["ml_anomaly_score_0_100"],
               color="red", marker="v", s=55, zorder=5, label="verified event-day")
    ax.set_ylabel("ml_anomaly_score_0_100")
    ax.set_title("Per-grid anomaly score distributions")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, "4_grid_comparison.png"), dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 4.5))
    daily = sc.groupby(["Date", "Grid_ID"])["ml_anomaly_score_0_100"].mean().unstack()
    bottom = np.zeros(len(daily))
    colors = ["#4477aa", "#66ccee", "#228833", "#ccbb44"]
    for col, c in zip(daily.columns, colors):
        ax.bar(daily.index, daily[col], width=2.5, color=c, alpha=0.85, label=col)
        bottom += np.nan_to_num(daily[col].to_numpy())
    evd = sc[sc["flood_event_active"] == 1]["Date"].unique()
    for d in evd:
        ax.axvline(pd.Timestamp(d), color="red", lw=1.2)
    ax.set_ylabel("mean daily anomaly score")
    ax.set_title("Daily mean anomaly score by grid (red lines = verified flood event-days)")
    ax.legend(ncol=4, fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, "5_daily_mean_by_grid.png"), dpi=150)
    plt.close(fig)

    logger.info("plots written to %s", PLOTS_DIR)


def main():
    scores, feat, df, card = run()

    rep("=" * 70)
    rep("VALIDATION CHECKS")
    rep("=" * 70)
    rep(f"duplicate Date+Grid_ID          : {int(scores.duplicated(['Date','Grid_ID']).sum())}")
    rep("flood_event_active used as input : NO (asserted in feature_preparation)")
    rep("road_density used as input       : NO (asserted in feature_preparation)")
    rep(f"infinite feature values          : 0 (asserted)")
    rep(f"scores rows                      : {len(scores)} (expected 16072)")

    ev_out, metrics = event_replay(scores)
    grid_analysis(scores)
    make_plots(scores, df)

    metrics.update({
        "model_card": card,
        "note": "Unsupervised anomaly detection; NOT a flood probability or official warning.",
    })
    with open(os.path.join(OUT_DIR, "model_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    logger.info("metrics saved")

    with open(os.path.join(OUT_DIR, "evaluation_console_output.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")


if __name__ == "__main__":
    main()
