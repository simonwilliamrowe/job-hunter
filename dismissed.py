"""
Job Hunter - Lista de ofertas DESCARTADAS.
El usuario puede descartar ofertas que no le interesan (aunque sean buenas
matches) y el sistema nunca más se las muestra, sin necesidad de aplicarlas.
"""
import json
import os
import threading
import time

DISMISSED_PATH = "data/dismissed.json"

_lock = threading.Lock()


def load():
    try:
        with open(DISMISSED_PATH, "r", encoding="utf-8") as f:
            items = json.load(f)
            return items if isinstance(items, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save(items):
    with _lock:
        with open(DISMISSED_PATH, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=1)


def ids():
    return {x.get("id") for x in load()}


def add(offer_id, company="", title="", source=""):
    items = load()
    if any(x.get("id") == offer_id for x in items):
        return items
    items.insert(0, {
        "id": offer_id,
        "company": company,
        "title": title,
        "source": source,
        "date": time.strftime("%Y-%m-%d"),
    })
    save(items)
    return items


def remove(offer_id):
    items = [x for x in load() if x.get("id") != offer_id]
    save(items)
    return items
