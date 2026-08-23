"""TEMPORARY DEMO BRANCH - prototype only.

Demonstrates viaSocket orchestration while the teammate's rule engine
does not exist yet.

This is an "ML anomaly status" label ONLY.
It is NOT a flood warning, NOT official flood risk, NOT a final
classification. It will be REMOVED once rule-engine integration lands.
"""

HIGH_ANOMALY_THRESHOLD = 75.0


def ml_anomaly_status(ml_anomaly_score):
    """Temporary two-way branch on the frozen ML anomaly score."""
    if float(ml_anomaly_score) >= HIGH_ANOMALY_THRESHOLD:
        return "HIGH ANOMALY"
    return "NORMAL/MODERATE ANOMALY"


def build_demo_message(ml_result):
    """Structured demo output block for viaSocket display."""
    status = ml_anomaly_status(ml_result["ml_anomaly_score"])
    return {
        "title": "Pune FloodShield - ML Anomaly Event",
        "date": ml_result["date"],
        "grid": ml_result["grid_id"],
        "ml_anomaly_score": ml_result["ml_anomaly_score"],
        "anomaly_percentile": ml_result["anomaly_percentile"],
        "status": status,
        "message": (
            "Hydro-meteorological conditions are unusually anomalous for "
            "this location. Awaiting rule-engine vulnerability assessment "
            "before issuing a final flood-risk classification."
        ),
        "disclaimer": (
            "ML anomaly status only - NOT a flood warning and NOT official "
            "flood risk."
        ),
    }


def render_demo_text(demo):
    return (
        f"{demo['title']}\n"
        f"Date: {demo['date']}\n"
        f"Grid: {demo['grid']}\n"
        f"ML anomaly score: {demo['ml_anomaly_score']}\n"
        f"Anomaly percentile: {demo['anomaly_percentile']}\n"
        f"Status: {demo['status']}\n"
        f"\nMessage:\n{demo['message']}\n"
        f"\n({demo['disclaimer']})"
    )
