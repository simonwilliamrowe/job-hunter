"""applied.py - Tracking de ofertas aplicadas.

Persiste en data/applied.json: lista de ofertas que el usuario marcó como aplicadas.
"""
import json
import os

APPLIED_PATH = "data/applied.json"


def _load():
    if not os.path.exists(APPLIED_PATH):
        return []
    try:
        with open(APPLIED_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save(items):
    with open(APPLIED_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)


def add(offer_id, company="", title="", snapshot=None):
    """Marca una oferta como aplicada. Idempotente."""
    items = _load()
    if any(i.get("id") == offer_id for i in items):
        return False
    from datetime import datetime
    item = {
        "id": offer_id,
        "company": company,
        "title": title,
        "applied_at": datetime.now().isoformat(timespec="seconds"),
    }
    if snapshot:
        item.update(snapshot)
    items.append(item)
    _save(items)
    return True


def ids():
    """Devuelve el set de IDs aplicadas."""
    return {i.get("id", "") for i in _load() if i.get("id")}


def all_items():
    return _load()
