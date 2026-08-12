"""
Job Hunter - Lista de ofertas APLICADAS.
El sistema las excluye siempre: la app web no las muestra y el briefing
diario de Telegram no las vuelve a mandar.
"""
import json
import os
import threading
import time

APPLIED_PATH = "data/applied.json"

_lock = threading.Lock()


def load():
    try:
        with open(APPLIED_PATH, "r", encoding="utf-8") as f:
            items = json.load(f)
            return items if isinstance(items, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save(items):
    with _lock:
        with open(APPLIED_PATH, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=1)


def ids():
    return {x.get("id") for x in load()}


def add(offer_id, company="", title="", source="", snapshot=None):
    """Registra una oferta como aplicada, GUARDANDO UNA COPIA COMPLETA
    (snapshot con descripción, link, salario...) para poder recuperarla
    exactamente aunque respondan meses después."""
    items = load()
    if any(x.get("id") == offer_id for x in items):
        return items
    entry = {
        "id": offer_id,
        "company": company,
        "title": title,
        "source": source,
        "date": time.strftime("%Y-%m-%d"),
    }
    if snapshot:
        entry["snapshot"] = snapshot  # copia completa de la oferta
    items.insert(0, entry)
    save(items)
    return items


def remove(offer_id):
    items = [x for x in load() if x.get("id") != offer_id]
    save(items)
    return items
