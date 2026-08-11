"""
Job Hunter - Application Tracker: registro de candidaturas y métricas
(Applications → Interviews → Offers, tasa por carril).
"""
import json
import os
import threading
import time
import uuid

TRACKER_PATH = "data/applications.json"

_lock = threading.Lock()

STATUSES = ["Review", "Applied", "Interview", "Offer", "Rejected", "Archived"]


def load():
    try:
        with open(TRACKER_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save(items):
    with _lock:
        with open(TRACKER_PATH, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)


def add(company, title, url="", track="", persona="", score=None, band="", status="Applied", notes=""):
    items = load()
    app = {
        "id": uuid.uuid4().hex[:10],
        "company": company,
        "title": title,
        "url": url,
        "track": track,
        "persona": persona,
        "score": score,
        "band": band,
        "status": status if status in STATUSES else "Applied",
        "date": time.strftime("%Y-%m-%d"),
        "notes": notes,
    }
    items.insert(0, app)
    save(items)
    return app


def update(app_id, fields):
    items = load()
    for a in items:
        if a["id"] == app_id:
            for k, v in fields.items():
                if k in ("company", "title", "url", "track", "persona", "score", "band", "notes"):
                    a[k] = v
                elif k == "status" and v in STATUSES:
                    a[k] = v
            save(items)
            return a
    return None


def stats():
    items = load()
    total = len(items)
    by_status = {}
    for a in items:
        by_status[a.get("status", "Review")] = by_status.get(a.get("status", "Review"), 0) + 1
    by_track = {}
    for a in items:
        t = a.get("track") or "sin carril"
        d = by_track.setdefault(t, {"applied": 0, "interviews": 0, "offers": 0})
        d["applied"] += 1
        if a.get("status") == "Interview":
            d["interviews"] += 1
        if a.get("status") == "Offer":
            d["offers"] += 1
            d["interviews"] += 1
    rates = {}
    for t, d in by_track.items():
        rates[t] = {
            "applied": d["applied"],
            "interview_rate": round(100 * d["interviews"] / d["applied"]) if d["applied"] else 0,
            "offer_rate": round(100 * d["offers"] / d["applied"]) if d["applied"] else 0,
        }
    return {"total": total, "by_status": by_status, "by_track": rates}
