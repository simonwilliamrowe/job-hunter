"""dismissed.py - Tracking de ofertas descartadas.

Persiste en data/dismissed.json: lista de ofertas que el usuario marcó
como 'no me interesa' o 'descartar' desde Telegram.
"""
import json
import os

DISMISSED_PATH = "data/dismissed.json"


def _load():
    if not os.path.exists(DISMISSED_PATH):
        return []
    try:
        with open(DISMISSED_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save(items):
    with open(DISMISSED_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)


def add(offer_id, company="", title=""):
    """Marca una oferta como descartada. Idempotente."""
    items = _load()
    if any(i.get("id") == offer_id for i in items):
        return False
    from datetime import datetime
    items.append({
        "id": offer_id,
        "company": company,
        "title": title,
        "dismissed_at": datetime.now().isoformat(timespec="seconds"),
    })
    _save(items)
    return True


def ids():
    """Devuelve el set de IDs descartadas."""
    return {i.get("id", "") for i in _load() if i.get("id")}


def all_items():
    return _load()
