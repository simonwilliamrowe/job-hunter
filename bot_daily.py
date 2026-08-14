"""Job Hunter - Bot diario v3.

Pipeline:
  1. Lee mensajes de Telegram (descartes y aplicadas)
  2. Descarga ofertas de fetchers (7 boards + 24 ATS)
  3. Pasa por matcher para scoring
  4. Genera briefing con 3 bandas (APPLY NOW, APPLY, REVIEW)
  5. Empaqueta top 3 en un ZIP con CV/carta/respuestas
  6. Envía todo a Telegram
"""

import json
import os
import re
import sys
import zipfile
from datetime import date

os.makedirs("data", exist_ok=True)

import requests

import applied
import cvgen
import dismissed
import fetchers
import matcher
import tracker
from profile_store import load_profile, load_personas

STATE_PATH = "data/seen.json"
BRIEF_PATH = "data/last_briefing.json"
OFFSET_PATH = "data/telegram_offset.txt"
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


# ============================================================================
# Telegram I/O
# ============================================================================

def _read_telegram_offset():
    try:
        return int(open(OFFSET_PATH).read().strip())
    except Exception:
        return 0


def _write_telegram_offset(offset):
    with open(OFFSET_PATH, "w") as f:
        f.write(str(offset))


def _get_telegram_updates():
    if not TOKEN or not CHAT_ID:
        return []
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/getUpdates",
            params={"offset": _read_telegram_offset(), "timeout": 2,
                    "allowed_updates": ["message"]},
            timeout=40,
        )
        return r.json().get("result", [])
    except Exception as e:
        print(f"[telegram] getUpdates error: {e}")
        return []


def _process_telegram_messages():
    """Lee Telegram UNA vez, aplica ambos parsers, avanza offset solo si matcheó."""
    if not TOKEN or not CHAT_ID:
        return 0, 0
    brief = load_briefing()
    if not brief:
        return 0, 0
    updates = _get_telegram_updates()
    applied_n = 0
    dismissed_n = 0
    last_id = _read_telegram_offset()
    matched_any = False
    for u in updates:
        last_id = max(last_id, u.get("update_id", 0))
        msg = u.get("message") or u.get("edited_message") or {}
        if str(msg.get("chat", {}).get("id", "")) != str(CHAT_ID):
            continue
        text = msg.get("text") or ""
        for oid in _parse_dismiss_message(text, brief):
            item = next((b for b in brief if b["id"] == oid), None)
            if item:
                dismissed.add(oid, company=item.get("company", ""),
                              title=item.get("title", ""))
                dismissed_n += 1
                matched_any = True
        for oid in _parse_apply_message(text, brief):
            item = next((b for b in brief if b["id"] == oid), None)
            if item:
                snapshot = {k: item.get(k) for k in
                            ("id", "title", "company", "url", "description",
                             "location", "salary", "tags", "source")}
                applied.add(oid, company=item.get("company", ""),
                            title=item.get("title", ""), snapshot=snapshot)
                applied_n += 1
                matched_any = True
    if matched_any:
        _write_telegram_offset(last_id + 1)
    return applied_n, dismissed_n


DISMISS_RE = re.compile(
    r"(?:descart\w*|no|fuera|quita|quit\w*|saca|elimin\w*)\s*"
    r"(?:a|la|las|el)?\s*:?\s*([0-9][0-9,\s+y]*)$", re.I)


def _parse_dismiss_message(text, brief):
    if not text or not brief:
        return []
    m = DISMISS_RE.search(text.strip())
    if not m:
        return []
    return [brief[int(t) - 1]["id"] for t in re.findall(r"\d+", m.group(1))
            if 1 <= int(t) <= len(brief)]


APPLY_RE = re.compile(
    r"(?:aplicad[oa]?|apliqu[ée])\s*(?:a|a la|a las)?\s*:?\s*([0-9][0-9,\s+y]*)$", re.I)


def _parse_apply_message(text, brief):
    if not text or not brief:
        return []
    t = text.lower().strip()
    marked = []
    m = APPLY_RE.search(t)
    if m:
        for tok in re.findall(r"\d+", m.group(1)):
            idx = int(tok)
            if 1 <= idx <= len(brief):
                marked.append(brief[idx - 1]["id"])
    else:
        for item in brief:
            url = (item.get("url") or "").lower().rstrip("/")
            if url and url in t:
                marked.append(item["id"])
    return marked


# ============================================================================
# Briefing
# ============================================================================

def load_seen():
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return set(json.load(f).get("ids", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_seen(ids):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"ids": sorted(ids)}, f, ensure_ascii=False, indent=1)


def save_briefing(jobs_list):
    """Guarda el briefing completo (con descripción) para archivar al marcar 'aplicada'."""
    data = []
    for j in jobs_list[:30]:
        data.append({
            "id": j.get("id", ""),
            "title": j.get("title", ""),
            "company": j.get("company", ""),
            "url": j.get("url", ""),
            "description": (j.get("description") or "")[:12000],
            "location": j.get("location", ""),
            "salary": j.get("salary", ""),
            "tags": (j.get("tags") or [])[:8],
            "source": j.get("source", ""),
        })
    with open(BRIEF_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def load_briefing():
    try:
        with open(BRIEF_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _offer_line(j, num=None):
    sal = f" · 💰 {j.get('salary') or ''}" if j.get("salary") else ""
    marker = j.get("salary_marker", {}).get("marker", "")
    prefix = f"{num}. " if num else ""
    track = j.get("track", "general")
    return (f"{prefix}[{j['score']}/100 {j['emoji']}] {j['title']} — {j['company']} ({track})"
            f"{sal} {marker}\n"
            f"   {j['url']}")


def build_briefing(scored, total):
    today = date.today().strftime("%d/%m/%Y")
    apply_now = [x for x in scored if x["band"] == "APPLY NOW"]
    apply = [x for x in scored if x["band"] == "APPLY"]
    review = [x for x in scored if x["band"] == "REVIEW"]

    lines = [
        f"🦅 JOB INTELLIGENCE — {today}",
        f"Ofertas revisadas: {total} · Top: {len(apply_now)}🔥 {len(apply)}🟢 {len(review)}🟡",
        "",
    ]
    num = 0
    for label, lst, detail in [("🔥 EXCEPTIONAL — APPLY NOW", apply_now[:5], True),
                                ("🟢 STRONG — APPLY", apply[:15], False),
                                ("🟡 SECONDARY — REVIEW", review[:20], False)]:
        if not lst:
            continue
        lines.append(f"{label} ({len(lst)})")
        for j in lst:
            num += 1
            lines.append(_offer_line(j, num=num))
            if detail:
                reasons = ", ".join(j.get("reasons", [])[:5])
                lines.append(f"  Why: {reasons}")
            lines.append("")
    if not apply_now and not apply:
        lines.append("Hoy no hay matches fuertes. Revisá las REVIEW manualmente.")
        lines.append("")
    lines.append("📌 ¿Aplicaste? Respondé: 'aplicada 1,3,5' y mañana ya no te la mando.")
    lines.append("📌 ¿No te interesa? Respondé: 'descartar 2,4' y la elimino para siempre.")
    return "\n".join(lines)


# ============================================================================
# Telegram send
# ============================================================================

def _notify_error(err_text):
    if TOKEN and CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                data={"chat_id": CHAT_ID, "text": f"⚠️ Job Hunter falló hoy:\n{err_text[:3500]}"},
                timeout=60,
            )
        except Exception:
            pass


def _send_telegram(text, zip_path=None):
    if not TOKEN or not CHAT_ID:
        return False
    try:
        api = f"https://api.telegram.org/bot{TOKEN}"
        # Telegram limit 4096 chars; mandamos en chunks si hace falta
        chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]
        for c in chunks:
            requests.post(f"{api}/sendMessage",
                          data={"chat_id": CHAT_ID, "text": c}, timeout=60).raise_for_status()
        if zip_path and os.path.exists(zip_path):
            with open(zip_path, "rb") as f:
                requests.post(f"{api}/sendDocument",
                              data={"chat_id": CHAT_ID,
                                    "caption": "📦 Top 3 con CV/carta/respuestas"},
                              files={"document": ("digest.zip", f, "application/zip")},
                              timeout=120).raise_for_status()
        return True
    except Exception as e:
        print(f"[telegram] error: {e}")
        return False


# ============================================================================
# Main
# ============================================================================

def main():
    try:
        return _main()
    except Exception:
        import traceback
        err = traceback.format_exc()
        print(err)
        _notify_error(err)
        return 1


def _main():
    print("🦅 Job Hunter — bot diario v3")

    # 1) Telegram (descartes y aplicadas)
    applied_n, dismissed_n = _process_telegram_messages()
    if applied_n:
        print(f"  aplicadas: {applied_n}")
    if dismissed_n:
        print(f"  descartadas: {dismissed_n}")

    # 2) Perfil
    profile = load_profile()

    # 3) Fetchers (7 boards + 24 ATS)
    print("Descargando ofertas…")
    jobs = fetchers.fetch_all(include_linkedin=False, include_ats=True)
    print(f"  {len(jobs)} ofertas únicas")

    # 4) Matcher
    applied_ids = applied.ids()
    dismissed_ids = dismissed.ids()
    scored = []
    for j in jobs:
        if j["id"] in applied_ids or j["id"] in dismissed_ids:
            continue
        s = matcher.score_offer(j, profile)
        if s["band"] in ("APPLY NOW", "APPLY", "REVIEW"):
            s["id"] = j["id"]
            s["title"] = j["title"]
            s["company"] = j["company"]
            s["url"] = j["url"]
            s["salary"] = j.get("salary", "")
            s["location"] = j.get("location", "")
            s["source"] = j.get("source", "")
            scored.append(s)

    # Orden: banda, luego score DESC
    order = {"APPLY NOW": 0, "APPLY": 1, "REVIEW": 2}
    scored.sort(key=lambda x: (order.get(x["band"], 9), -x["score"]))

    # 5) Save briefing (para archive al marcar aplicadas)
    save_briefing([{**j, **s} for j, s in zip(jobs[:30],
               [next((x for x in scored if x["id"] == j["id"]), {}) for j in jobs[:30]])])

    # 6) Build briefing
    seen = load_seen()
    briefing = build_briefing(scored, len(jobs))
    new_ids = [x["id"] for x in scored[:20] if x["id"] not in seen]
    seen.update(x["id"] for x in scored[:20])
    save_seen(seen)

    print("\n" + briefing + "\n")

    # 7) ZIP top 3 con CV/carta
    zip_path = None
    if scored:
        try:
            zip_path = "digest.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for x in scored[:3]:
                    job = next((j for j in jobs if j["id"] == x["id"]), None)
                    if not job:
                        continue
                    pkg = cvgen.generate_package(profile, job,
                                                  track=x.get("track", "general"),
                                                  out_dir="generated")
                    for f in pkg.get("files", []):
                        zf.write(f["path"], os.path.join(
                            pkg.get("dir") or pkg.get("offer_id", "x"), f["name"]))
            print(f"📦 Paquetes del top 3 → {zip_path}")
        except Exception as e:
            print(f"[zip] error: {e}")
            zip_path = None

    # 8) Telegram
    if _send_telegram(briefing, zip_path):
        print("✅ Resumen enviado a Telegram")
    else:
        print("ℹ️  Sin secrets: briefing solo en logs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
