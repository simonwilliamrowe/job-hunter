"""
Job Hunter - Carga/guardado del perfil maestro, personas y respuestas.
"""
import json
import re
import threading

PROFILE_PATH = "data/profile.json"
PERSONAS_PATH = "data/personas.json"

_lock = threading.Lock()


def load_profile(path=PROFILE_PATH):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"name": "Tu Nombre", "headline": "Tu perfil", "skills": {},
                "experience": [], "independent_experience": [], "answers": {},
                "salary": {"floor": 1000, "target_min": 1300, "target_max": 2000},
                "availability": {}, "languages": [], "extra_keywords": []}


def save_profile(profile, path=PROFILE_PATH):
    with _lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)


def load_personas(path=PERSONAS_PATH):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_personas(personas, path=PERSONAS_PATH):
    with _lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(personas, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# formato de bloques legible (# Rol — Empresa (Fechas) / - bullet)
# ---------------------------------------------------------------------------

HEADER_RE = re.compile(r"^\s*#\s*(.+?)\s*$")
BULLET_RE = re.compile(r"^\s*[-•]\s*(.+?)\s*$")


def parse_blocks(text, section="professional"):
    entries, current = [], None
    for line in (text or "").splitlines():
        m = HEADER_RE.match(line)
        if m:
            current = {"id": f"e{len(entries)}", "section": section, "role": "",
                       "company": "", "dates": "", "bullets": []}
            entries.append(current)
            parts = [p.strip() for p in m.group(1).split("—")]
            if len(parts) >= 2:
                current["role"] = parts[0]
                rest = "—".join(parts[1:])
                dm = re.search(r"\((.*?)\)\s*$", rest)
                if dm:
                    current["company"] = rest[:dm.start()].strip()
                    current["dates"] = dm.group(1).strip()
                else:
                    current["company"] = rest
            else:
                current["role"] = m.group(1)
            continue
        mb = BULLET_RE.match(line)
        if mb and current is not None:
            current["bullets"].append(mb.group(1))
    return entries


def blocks_to_text(entries):
    lines = []
    for e in entries or []:
        hdr = e.get("role", "")
        rest = e.get("company", "")
        if e.get("dates"):
            rest = f"{rest} ({e['dates']})"
        if rest:
            hdr = f"{hdr} — {rest}"
        lines.append(f"# {hdr}")
        for b in e.get("bullets", []):
            lines.append(f"- {b}")
        lines.append("")
    return "\n".join(lines).rstrip()
