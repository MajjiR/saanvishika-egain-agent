"""Catalog lookup, fictional test orders, and a small SQLite record store."""

import json
import os
import re
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))
HERE = Path(__file__).parent
CATALOG = json.loads((HERE / "catalog.json").read_text(encoding="utf-8"))

_STOP = {"the", "a", "an", "with", "and", "for", "of", "set", "jewellery", "jewelry", "pcs", "pieces"}


def _tokens(text: str) -> set:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP and len(t) > 1}


def search_products(query: str = "", max_price: float | None = None, limit: int = 3, available_only=True):
    q = _tokens(query or "")
    scored = []
    for p in CATALOG:
        if available_only and not p["available"]:
            continue
        if max_price is not None and p["price"] > max_price:
            continue
        hay = _tokens(p["title"] + " " + " ".join(p["tags"]))
        desc = _tokens(p["description"])
        score = 3 * len(q & hay) + len(q & desc) if q else 1
        if score > 0:
            scored.append((score, -p["price"] if not q else 0, p))
    scored.sort(key=lambda s: (-s[0], s[1]))
    return [s[2] for s in scored[:limit]], (scored[0][0] if scored else 0), (scored[1][0] if len(scored) > 1 else 0)


def find_product(query: str):
    """Best single match, or None plus up to 3 candidates when unsure."""
    results, top, second = search_products(query, limit=3, available_only=False)
    if not results:
        return None, []
    q = _tokens(query)
    for p in results:  # exact name typed or pasted
        if query.strip().lower() == p["title"].lower():
            return p, results
    best = results[0]
    covered = len(q & _tokens(best["title"])) / max(1, len(q))
    if len(q) >= 2 and covered >= 0.6 and top > second:
        return best, results
    return None, results


def _now():
    return datetime.now(IST)


def test_orders():
    """Fictional orders, dated relative to now so the demo never goes stale."""
    n = _now()
    return {
        "SV1001": {"status": "shipped", "item": "Emerald Screwback Jhumka", "value": 1299, "phone_last4": "1111",
                   "placed": n - timedelta(days=2), "courier": "Delhivery", "awb": "DLV55120931", "eta_days": 3},
        "SV1002": {"status": "delivered", "item": "Grand Floral AD Stone Jhumka Earrings", "value": 1499, "phone_last4": "2222",
                   "placed": n - timedelta(days=5), "delivered": n - timedelta(hours=20)},
        "SV1003": {"status": "delivered", "item": "Antique Studs (Screw Back) - Ruby", "value": 1199, "phone_last4": "3333",
                   "placed": n - timedelta(days=14), "delivered": n - timedelta(days=10)},
        "SV1004": {"status": "processing", "item": "Designer Gemstone Neck Patti Ruby", "value": 1099, "phone_last4": "4444",
                   "placed": n - timedelta(hours=6)},
        "SV1005": {"status": "delivered", "item": "Bridal Triple Gemstone CZ Diamond Necklace Set", "value": 4999,
                   "phone_last4": "5555", "placed": n - timedelta(days=6), "delivered": n - timedelta(days=3)},
        "SV1006": {"status": "delivered", "item": "Solitaire Drop Stud Earrings (Green)", "value": 659, "phone_last4": "6666",
                   "placed": n - timedelta(days=4), "delivered": n - timedelta(days=1), "prior_claims": 3},
    }


class DB:
    def __init__(self, path: str):
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, kind TEXT, dedupe TEXT, created TEXT, data TEXT)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS ix_dedupe ON records(kind, dedupe)")
        self.conn.commit()

    def find(self, kind: str, dedupe: str):
        row = self.conn.execute("SELECT data FROM records WHERE kind=? AND dedupe=?", (kind, dedupe)).fetchone()
        return json.loads(row[0]) if row else None

    def add(self, kind: str, prefix: str, dedupe: str, data: dict) -> dict:
        with self.lock:
            existing = self.find(kind, dedupe) if dedupe else None
            if existing:
                return {**existing, "repeat": True}
            count = self.conn.execute("SELECT COUNT(*) FROM records WHERE kind=?", (kind,)).fetchone()[0]
            rid = f"{prefix}-{1001 + count}"
            data = {**data, "id": rid, "created": _now().isoformat(timespec="seconds")}
            self.conn.execute("INSERT INTO records VALUES (?,?,?,?,?)",
                              (rid, kind, dedupe, data["created"], json.dumps(data, ensure_ascii=False)))
            self.conn.commit()
            return data

    def update(self, rid: str, **fields):
        with self.lock:
            row = self.conn.execute("SELECT data FROM records WHERE id=?", (rid,)).fetchone()
            if not row:
                return None
            data = {**json.loads(row[0]), **fields}
            self.conn.execute("UPDATE records SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), rid))
            self.conn.commit()
            return data

    def get(self, rid: str):
        row = self.conn.execute("SELECT data FROM records WHERE id=?", (rid,)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, limit=100):
        rows = self.conn.execute("SELECT data FROM records ORDER BY created DESC LIMIT ?", (limit,)).fetchall()
        return [json.loads(r[0]) for r in rows]


def open_db():
    return DB(os.environ.get("DB_PATH", str(HERE.parent / "data.sqlite3")))
