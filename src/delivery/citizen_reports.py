"""Citizen report intake (Module 5 capability).

Stores ONLY what citizens actually submit (validated). No fabricated
reports. Appends to a CSV store; returns an ID + status.
"""

import csv
import json
import logging
import os
import uuid
from datetime import datetime, timezone

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

_DIR = os.path.dirname(__file__)


def _store_path():
    cfg = json.load(open(os.path.join(_DIR, "delivery_config.json")))
    return cfg["citizen_reporting"]["store"]


def submit_report(grid_id, report_type, description, timestamp=None):
    from src.risk.rule_engine import VALID_GRID_IDS

    cfg = json.load(open(os.path.join(_DIR, "delivery_config.json")))
    cr = cfg["citizen_reporting"]

    if grid_id not in VALID_GRID_IDS:
        raise ValueError(f"unknown grid_id {grid_id!r}")
    if report_type not in cr["report_types"]:
        raise ValueError(f"report_type must be one of {cr['report_types']}")
    if timestamp is None:
        ts = datetime.now(timezone.utc).isoformat()
    else:
        ts = pd.Timestamp(timestamp).isoformat()
    if description is None or not str(description).strip():
        raise ValueError("description required")

    path = _store_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    exists = os.path.exists(path)
    report_id = "CR-" + uuid.uuid4().hex[:12].upper()

    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["report_id", "grid_id", "report_type",
                        "description", "timestamp", "status"])
        w.writerow([report_id, grid_id, report_type,
                    str(description), ts, "SUBMITTED"])

    logger.info("citizen report stored: %s (%s / %s)", report_id, grid_id, report_type)
    return {"report_id": report_id, "status": "SUBMITTED"}


def list_reports(grid_id=None, limit=50):
    path = _store_path()
    if not os.path.exists(path):
        return []
    df = pd.read_csv(path)
    if grid_id:
        df = df[df.grid_id == grid_id]
    return df.tail(limit).to_dict("records")
