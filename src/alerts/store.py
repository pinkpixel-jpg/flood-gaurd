"""Two physically SEPARATE alert databases (enforced separation):

    data/public_alerts.db     -> PUBLIC citizen-friendly alerts + prefs
    data/municipal_alerts.db  -> MUNICIPAL operational alerts + prefs

No risk/environment datasets are duplicated here — alerts store the
generated notification payload only.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PUBLIC_DB = "data/public_alerts.db"
MUNICIPAL_DB = "data/municipal_alerts.db"


def _conn(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c


def _now():
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------- PUBLIC ----

def init_public():
    with _conn(PUBLIC_DB) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS public_alerts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, grid_id TEXT NOT NULL,
            risk_level TEXT NOT NULL, risk_score REAL NOT NULL,
            trend TEXT, simple_explanation TEXT, safety_recommendation TEXT,
            mode TEXT, created_at TEXT NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS public_prefs(
            username TEXT NOT NULL, grid_id TEXT NOT NULL,
            min_level TEXT NOT NULL DEFAULT 'LOW',
            PRIMARY KEY (username, grid_id))""")


def insert_public_alert(date, grid_id, risk_level, risk_score, trend,
                        explanation, recommendation):
    init_public()
    with _conn(PUBLIC_DB) as c:
        cur = c.execute(
            "INSERT INTO public_alerts(date,grid_id,risk_level,risk_score,"
            "trend,simple_explanation,safety_recommendation,mode,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (date, grid_id, risk_level, risk_score, trend, explanation,
             recommendation, "HISTORICAL_REPLAY", _now()))
        return cur.lastrowid


def list_public(limit=50):
    init_public()
    with _conn(PUBLIC_DB) as c:
        rows = c.execute("SELECT * FROM public_alerts "
                         "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def set_public_pref(username, grid_id, min_level):
    init_public()
    with _conn(PUBLIC_DB) as c:
        c.execute("INSERT OR REPLACE INTO public_prefs VALUES (?,?,?)",
                  (username, grid_id, min_level))


def get_public_pref(username):
    init_public()
    with _conn(PUBLIC_DB) as c:
        rows = c.execute("SELECT grid_id, min_level FROM public_prefs "
                         "WHERE username=?", (username,)).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------- MUNICIPAL ----

def init_municipal():
    with _conn(MUNICIPAL_DB) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS municipal_alerts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, grid_id TEXT NOT NULL,
            risk_score REAL NOT NULL, risk_components TEXT NOT NULL,
            vulnerability_score REAL, vulnerability_level TEXT,
            trend TEXT, prevention_priority TEXT,
            actions_json TEXT NOT NULL, checklist_json TEXT NOT NULL,
            environment_json TEXT, citizen_reports INTEGER DEFAULT 0,
            mode TEXT, created_at TEXT NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS municipal_prefs(
            username TEXT NOT NULL, grid_id TEXT NOT NULL,
            min_priority TEXT NOT NULL DEFAULT 'ELEVATED',
            PRIMARY KEY (username, grid_id))""")


def insert_municipal_alert(date, grid_id, payload):
    """payload = normalized municipal alert dict (see generate.py)."""
    init_municipal()
    with _conn(MUNICIPAL_DB) as c:
        cur = c.execute(
            "INSERT INTO municipal_alerts(date,grid_id,risk_score,"
            "risk_components,vulnerability_score,vulnerability_level,trend,"
            "prevention_priority,actions_json,checklist_json,"
            "environment_json,citizen_reports,mode,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (date, grid_id, payload["risk"]["score"],
             json.dumps(payload["risk"]["components"]),
             payload["vulnerability"]["score"],
             payload["vulnerability"]["level"], payload["risk"]["trend"],
             payload["prevention"]["priority"],
             json.dumps(payload["prevention"]["recommended_actions"]),
             json.dumps(payload["prevention"]["checklist"]),
             json.dumps(payload["environment"]),
             payload["citizen_reports"]["count"], payload["metadata"]["mode"],
             _now()))
        return cur.lastrowid


def list_municipal(limit=50):
    init_municipal()
    with _conn(MUNICIPAL_DB) as c:
        rows = c.execute("SELECT * FROM municipal_alerts "
                         "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        for k in ("risk_components", "actions_json", "checklist_json",
                  "environment_json"):
            d[k] = json.loads(d[k])
        out.append(d)
    return out


def set_municipal_pref(username, grid_id, min_priority):
    init_municipal()
    with _conn(MUNICIPAL_DB) as c:
        c.execute("INSERT OR REPLACE INTO municipal_prefs VALUES (?,?,?)",
                  (username, grid_id, min_priority))


def get_municipal_pref(username):
    init_municipal()
    with _conn(MUNICIPAL_DB) as c:
        rows = c.execute("SELECT grid_id, min_priority FROM municipal_prefs "
                         "WHERE username=?", (username,)).fetchall()
    return [dict(r) for r in rows]
