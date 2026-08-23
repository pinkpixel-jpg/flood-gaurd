"""Authentication for the dual alert systems.

- Passwords: PBKDF2-HMAC-SHA256 (120k iters) with per-user salt.
- Sessions: opaque bearer tokens (hashed at rest), 24 h expiry.
- Roles: PUBLIC and MUNICIPAL only.

Demo accounts are seeded automatically and are FOR DEMO USE ONLY:
    citizen   / citizen-demo     (PUBLIC)
    municipal / municipal-demo   (MUNICIPAL)
"""

import hashlib
import json
import logging
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USERS_DB = "data/alerts_users.db"
ROLES = ("PUBLIC", "MUNICIPAL")
SESSION_HOURS = 24

SEED_USERS = [
    {"username": "citizen", "password": "citizen-demo", "role": "PUBLIC"},
    {"username": "municipal", "password": "municipal-demo", "role": "MUNICIPAL"},
]


def _conn():
    os.makedirs(os.path.dirname(USERS_DB), exist_ok=True)
    c = sqlite3.connect(USERS_DB)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            username TEXT PRIMARY KEY,
            pw_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('PUBLIC','MUNICIPAL')))""")
        c.execute("""CREATE TABLE IF NOT EXISTS sessions(
            token_hash TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            expires_utc TEXT NOT NULL)""")
        for u in SEED_USERS:
            if not c.execute("SELECT 1 FROM users WHERE username=?",
                             (u["username"],)).fetchone():
                c.execute("INSERT INTO users VALUES (?,?,?)",
                          (u["username"], hash_password(u["password"]), u["role"]))
                logger.info("seeded demo user: %s (%s)", u["username"], u["role"])


def hash_password(password):
    salt = secrets.token_urlsafe(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000)
    return f"pbkdf2${salt}${dk.hex()}"


def verify_password(password, stored):
    try:
        _, salt, hexdigest = stored.split("$")
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000)
    return secrets.compare_digest(dk.hex(), hexdigest)


def login(username, password):
    """Return session dict on success; None on bad credentials."""
    init_db()
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE username=?",
                        (username,)).fetchone()
    if not row or not verify_password(password, row["pw_hash"]):
        return None
    token = secrets.token_urlsafe(32)
    th = hashlib.sha256(token.encode()).hexdigest()
    exp = (datetime.now(timezone.utc) +
           timedelta(hours=SESSION_HOURS)).isoformat()
    with _conn() as c:
        c.execute("INSERT INTO sessions VALUES (?,?,?,?)",
                  (th, row["username"], row["role"], exp))
    return {"token": token, "username": row["username"], "role": row["role"],
            "expires": exp}


def resolve_token(token):
    """Return {username, role} for a live session token, else None."""
    if not token:
        return None
    th = hashlib.sha256(token.encode()).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        row = c.execute("SELECT * FROM sessions WHERE token_hash=? AND expires_utc > ?",
                        (th, now)).fetchone()
    return {"username": row["username"], "role": row["role"]} if row else None


def require_role(auth_header, roles):
    """Parse 'Authorization: Bearer <t>' and enforce role membership."""
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, ("missing_bearer_token", 401)
    ident = resolve_token(auth_header.split(" ", 1)[1].strip())
    if not ident:
        return None, ("invalid_or_expired_session", 401)
    if ident["role"] not in roles:
        return None, (f"role '{ident['role']}' not authorised here", 403)
    return ident, None


if __name__ == "__main__":
    init_db()
    s = login("citizen", "citizen-demo")
    print(json.dumps({**s, "token": s["token"][:12] + "..."}))
    print("resolve:", resolve_token(s["token"]))
