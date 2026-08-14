"""profile_store.py - Carga del perfil y personas desde data/.

El perfil canónico está en data/profile.json.
Las personas (variantes de CV) están en data/personas.json.
"""

import json
import os


def load_profile():
    """Carga el perfil del candidato."""
    path = "data/profile.json"
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_personas():
    """Carga las personas (variantes de CV)."""
    path = "data/personas.json"
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_profile(profile):
    path = "data/profile.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=1)
