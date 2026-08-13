"""
Job Hunter - BOT DIARIO v2 (app viva en GitHub Actions).

Cada mañana: descarga ofertas de 7 bolsas → scoring multi-carril →
briefing (grupos 🔥🟢🟡 + top 3 con desglose y CV recomendado) →
paquetes del top 3 en un zip → Telegram.

NUNCA se postula solo: la IA encuentra y prepara, vos aprobás y aplicás.

Cambios v2.1:
- Logs verbosos de Telegram para diagnosticar problemas con applied/dismissed.
- Mantiene la lógica original: las ofertas crypto/top vuelven a salir
  cada día si siguen activas (no hay anti-spam de "ya visto"). Solo
  applied.json y dismissed.json filtran duro.
"""
import json
import os
import re
import sys
import zipfile
from datetime import date

os.makedirs("data", exist_ok=True)  # la carpeta data/ siempre existe

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


def load_seen():
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return set(json.load(f).get("ids", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_briefing(jobs_list):
    """Guarda el orden del briefing con COPIA COMPLETA de cada oferta
    (descripción incluida) para poder archivar la exacta al marcar 'aplicada'."""
    data = [{"id": j["id"], "title": j["title"], "company": j["company"],
             "url": j["url"], "description": (j.get("description") or "")[:12000],
             "location": j.get("location") or "", "salary": j.get("salary") or "",
             "tags": (j.get("tags") or [])[:8], "source": j.get("source") or ""}
            for j in jobs_list[:20]]
    with open(BRIEF_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def load_briefing():
    try:
        with open(BRIEF_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


# Parser para "descartar 2,4" / "no 3" / "fuera 1 y 5" / "descarta 2,4,5,7"
# Acepta: "descartar", "descarta", "descarté", "no", "fuera", "quita", "quit",
# "saca", "elimina" + números separados por coma, espacio o "y"
DISMISS_RE = re.compile(
    r"(?:descart\w*|no|fuera|quita|quit\w*|saca|elimin\w*)\s*"
    r"(?:a|la|las|el)?\s*:?\s*"
    r"([0-9](?:[0-9,\s+y]*[0-9])?)\s*$",
    re.I)


def _parse_dismiss_message(text, brief):
    """Interpreta 'descartar 2,4' o 'no 3' o 'fuera 1 y 5'.
    Devuelve lista de ids de ofertas a descartar."""
    if not text or not brief:
        return []
    m = DISMISS_RE.search(text.strip())
    if not m:
        return []
    marked = []
    for tok in re.findall(r"\d+", m.group(1)):
        idx = int(tok)
        if 1 <= idx <= len(brief):
            marked.append(brief[idx - 1]["id"])
    return marked


def _process_telegram_dismissals():
    """Lee mensajes de descarte y los guarda. Devuelve nº de descartados."""
    if not TOKEN or not CHAT_ID:
        print("[telegram] Sin TOKEN o CHAT_ID — no se procesan descartes")
        return 0
    brief = load_briefing()
    if not brief:
        print("[telegram] Sin briefing previo — no se procesan descartes")
        return 0
    offset = 0
    try:
        offset = int(open(OFFSET_PATH).read().strip())
    except Exception as e:
        print(f"[telegram] No hay offset previo: {e}")
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/getUpdates",
            params={"offset": offset, "timeout": 2}, timeout=40,
        )
        data = r.json()
        updates = data.get("result", [])
        if not updates and "description" in data:
            print(f"[telegram] Respuesta inesperada: {str(data)[:200]}")
    except Exception as e:
        print(f"[telegram] getUpdates error: {e}")
        return 0
    marked = 0
    last_id = offset
    print(f"[telegram] Leyendo updates desde offset {offset}...")
    for u in updates:
        last_id = max(last_id, u.get("update_id", 0))
        msg = u.get("message") or u.get("edited_message") or {}
        chat_id = str(msg.get("chat", {}).get("id", ""))
        if chat_id != str(CHAT_ID):
            continue
        text = msg.get("text") or ""
        print(f"[telegram]   mensaje: {text!r}")
        ids_to_dismiss = _parse_dismiss_message(text, brief)
        if not ids_to_dismiss:
            print(f"[telegram]     no matchea ningún patrón de descarte")
            continue
        print(f"[telegram]     matchea: {ids_to_dismiss}")
        for oid in ids_to_dismiss:
            item = next((b for b in brief if b["id"] == oid), None)
            if item:
                dismissed.add(oid, company=item.get("company", ""), title=item.get("title", ""))
                marked += 1
                print(f"[telegram]     ✓ descartada: {item.get('title','')[:50]}")
    if last_id:
        with open(OFFSET_PATH, "w") as f:
            f.write(str(last_id + 1))
    if marked:
        print(f"✅ Descartadas desde Telegram: {marked}")
    else:
        print(f"[telegram] Ningún mensaje procesado como descarte")
    return marked


def _parse_apply_message(text, brief):
    """Interpreta 'aplicada 1,3,5' o 'aplique a 1 y 3' o un link de oferta.
    Devuelve lista de ids de ofertas a marcar como aplicadas."""
    if not text or not brief:
        return []
    t = text.lower().strip()
    marked = []
    # patrón: aplicada/apliqué/aplicado/aplicó [a] 1,3,5
    m = re.search(r"(?:aplicad[oa]?|apliqu[ée])\s*(?:a|a la|a las)?\s*:?\s*([0-9](?:[0-9,\s+y]*[0-9])?)\s*$", t)
    if m:
        for tok in re.findall(r"\d+", m.group(1)):
            idx = int(tok)
            if 1 <= idx <= len(brief):
                marked.append(brief[idx - 1]["id"])
    else:
        # link directo de una oferta del briefing
        for item in brief:
            url = (item.get("url") or "").lower().rstrip("/")
            if url and url in t:
                marked.append(item["id"])
    return marked


def _process_telegram_applications():
    """Lee los mensajes que el usuario le mandó al bot y marca aplicadas.
    Devuelve el número de ofertas marcadas."""
    if not TOKEN or not CHAT_ID:
        print("[telegram] Sin TOKEN o CHAT_ID — no se procesan aplicadas")
        return 0
    brief = load_briefing()
    if not brief:
        print("[telegram] Sin briefing previo — no se procesan aplicadas")
        return 0
    offset = 0
    try:
        offset = int(open(OFFSET_PATH).read().strip())
    except Exception as e:
        print(f"[telegram] No hay offset previo: {e}")
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/getUpdates",
            params={"offset": offset, "timeout": 2}, timeout=40,
        )
        data = r.json()
        updates = data.get("result", [])
        if not updates and "description" in data:
            print(f"[telegram] Respuesta inesperada: {str(data)[:200]}")
    except Exception as e:
        print(f"[telegram] getUpdates error: {e}")
        return 0
    marked = 0
    last_id = offset
    print(f"[telegram] Leyendo updates desde offset {offset}...")
    for u in updates:
        last_id = max(last_id, u.get("update_id", 0))
        msg = u.get("message") or u.get("edited_message") or {}
        chat_id = str(msg.get("chat", {}).get("id", ""))
        if chat_id != str(CHAT_ID):
            continue
        text = msg.get("text") or ""
        print(f"[telegram]   mensaje: {text!r}")
        ids_to_mark = _parse_apply_message(text, brief)
        if not ids_to_mark:
            print(f"[telegram]     no matchea ningún patrón de aplicada")
            continue
        print(f"[telegram]     matchea: {ids_to_mark}")
        for oid in ids_to_mark:
            item = next((b for b in brief if b["id"] == oid), None)
            if item:
                snapshot = {k: item.get(k) for k in
                            ("id", "title", "company", "url", "description",
                             "location", "salary", "tags", "source")}
                applied.add(oid, company=item.get("company", ""),
                            title=item.get("title", ""), snapshot=snapshot)
                marked += 1
                print(f"[telegram]     ✓ aplicada: {item.get('title','')[:50]}")
    if last_id:
        with open(OFFSET_PATH, "w") as f:
            f.write(str(last_id + 1))
    if marked:
        print(f"✅ Marcadas como aplicadas desde Telegram: {marked}")
    return marked


def save_seen(ids):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"ids": sorted(ids)}, f, ensure_ascii=False, indent=1)


def build_briefing(scored, total):
    """Genera el briefing. Ya no usa 'seen' para filtrar (las mejores ofertas
    vuelven a salir cada día si siguen activas en el mercado)."""
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
    if apply_now:
        lines.append(f"🔥 EXCEPTIONAL ({len(apply_now)}) — APPLY NOW")
        for j in apply_now[:5]:
            num += 1
            lines.append(_offer_line(j, detail=True, num=num))
        lines.append("")
    if apply:
        lines.append(f"🟢 STRONG ({len(apply)}) — APPLY")
        for j in apply[:8]:
            num += 1
            lines.append(_offer_line(j, num=num))
        lines.append("")
    if review:
        lines.append(f"🟡 SECONDARY ({len(review)}) — REVIEW")
        for j in review[:6]:
            num += 1
            lines.append(_offer_line(j, num=num))
        lines.append("")
    if not apply_now and not apply:
        lines.append("Hoy no hay matches fuertes. Revisá las REVIEW manualmente.")
    lines.append("")
    lines.append("📌 ¿Aplicaste a alguna? Respondé: 'aplicada 1,3,5' y no te la vuelvo a mandar.")
    lines.append("📌 ¿Alguna no te interesa? Respondé: 'descartar 2,4' (o 'no 2') y la elimino para siempre.")
    return "\n".join(lines)


def _offer_line(j, detail=False, num=None):
    sal = f" · 💰 {j.get('salary') or ''}" if j.get("salary") else ""
    marker = j.get("salary_marker", {}).get("marker", "")
    prefix = f"{num}. " if num else ""
    line = (f"{prefix}[{j['score']}/100 {j['emoji']}] {j['title']} — {j['company']} ({j['track_label']})"
            f"{sal} {marker}\n"
            f"   {j['url']}")
    if detail:
        reasons = ", ".join(j.get("reasons", [])[:5])
        pkg = j.get("persona", "")
        line += (f"\n  Why: {reasons}\n"
                 f"  CV: {pkg} · ~{_est_minutes(pkg)} min de aplicación")
    return line


def _est_minutes(persona_id):
    personas = load_personas()
    p = personas.get(persona_id, {})
    return p.get("est_minutes", 6)


def _notify_error(err_text):
    """Si hay secrets, manda el error a Telegram para que el usuario lo vea."""
    if TOKEN and CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                data={"chat_id": CHAT_ID, "text": f"⚠️ Job Hunter falló hoy:\n{err_text[:3500]}"},
                timeout=60,
            )
        except Exception:  # noqa: BLE001
            pass


def main():
    try:
        return _main()
    except Exception as e:  # noqa: BLE001
        import traceback
        err = traceback.format_exc()
        print(err)
        _notify_error(err)
        return 1


def _main():
    print("🦅 Job Hunter — bot diario v2.1 (logs verbosos)")
    # Estado previo
    print(f"  Estado previo: applied={len(applied.ids())} | dismissed={len(dismissed.ids())}")

    # 1) Procesar mensajes de Telegram ANTES de descargar ofertas
    marked = _process_telegram_applications()
    if marked:
        print(f"  (se excluirán {marked} ofertas ya aplicadas)")
    dismissed_n = _process_telegram_dismissals()
    if dismissed_n:
        print(f"  (se excluirán {dismissed_n} ofertas descartadas)")

    # 2) Cargar perfil y descargar ofertas
    profile = load_profile()
    keywords_ok = bool(profile.get("skills"))
    if not keywords_ok:
        print("⚠️  PERFIL DE EJEMPLO: cargá tu perfil real (data/profile.json).")
    print("Descargando ofertas…")
    jobs = fetchers.fetch_all()
    print(f"  {len(jobs)} ofertas únicas")

    # 3) Filtrar aplicadas/descartadas, matchear el resto
    applied_ids = applied.ids()
    dismissed_ids = dismissed.ids()
    print(f"  Filtro: {len(applied_ids)} aplicadas + {len(dismissed_ids)} descartadas")

    scored = []
    for j in jobs:
        if j["id"] in applied_ids or j["id"] in dismissed_ids:
            continue
        s = matcher.score_offer(j, profile)
        if s["band"] in ("APPLY NOW", "APPLY", "REVIEW"):
            s["id"] = j["id"]
            s.update({k: j[k] for k in ("title", "company", "url", "salary")})
            s["matched"] = matcher.family_match(j, profile)
            scored.append(s)
    order = {"APPLY NOW": 0, "APPLY": 1, "REVIEW": 2}
    scored.sort(key=lambda x: (order.get(x["band"], 9), -x["score"]))
    print(f"  Matcheadas: {len(scored)} ({sum(1 for s in scored if s['band']=='APPLY NOW')} APPLY NOW, {sum(1 for s in scored if s['band']=='APPLY')} APPLY, {sum(1 for s in scored if s['band']=='REVIEW')} REVIEW)")

    # 4) Guardar briefing y construir mensaje
    save_briefing(scored[:20])
    briefing = build_briefing(scored, len(jobs))

    # 5) Actualizar seen.json (solo para tracking, no se usa para filtrar)
    seen = load_seen()
    seen.update(x["id"] for x in scored[:12])
    save_seen(seen)

    print("\n" + briefing + "\n")

    # 6) Generar ZIP con los 3 paquetes top
    zip_path = None
    if scored:
        zip_path = "digest.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for x in scored[:3]:
                job = next((j for j in jobs if j["id"] == x["id"]), None)
                if not job:
                    continue
                pkg = cvgen.generate_package(profile, job, track=x["track"], out_dir="generated")
                for f in pkg["files"]:
                    zf.write(f["path"], os.path.join(pkg.get("dir") or pkg["offer_id"], f["name"]))
        print(f"📦 Paquetes del top 3 → {zip_path}")

    # 7) Enviar a Telegram
    sent = False
    if TOKEN and CHAT_ID:
        try:
            api = f"https://api.telegram.org/bot{TOKEN}"
            requests.post(f"{api}/sendMessage",
                          data={"chat_id": CHAT_ID, "text": briefing[:4000]}, timeout=60).raise_for_status()
            if zip_path:
                with open(zip_path, "rb") as f:
                    requests.post(f"{api}/sendDocument",
                                  data={"chat_id": CHAT_ID,
                                        "caption": "📦 Paquetes CV del top 3 (ATS .docx + .txt + carta + respuestas). ¡Aplicá vos!"},
                                  files={"document": ("digest.zip", f, "application/zip")}, timeout=120).raise_for_status()
            sent = True
        except Exception as e:  # noqa: BLE001
            print(f"[telegram] error: {e}")
    if sent:
        print("✅ Resumen enviado a Telegram")
    else:
        print("ℹ️  Sin secrets de Telegram: el briefing quedó arriba (y en logs del workflow).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
