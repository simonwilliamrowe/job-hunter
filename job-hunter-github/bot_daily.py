"""
Job Hunter - BOT DIARIO v2 (app viva en GitHub Actions).

Cada mañana: descarga ofertas de 7 bolsas → scoring multi-carril →
briefing (grupos 🔥🟢🟡 + top 3 con desglose y CV recomendado) →
paquetes del top 3 en un zip → Telegram.

NUNCA se postula solo: la IA encuentra y prepara, vos aprobás y aplicás.
"""
import json
import os
import sys
import zipfile
from datetime import date

os.makedirs("data", exist_ok=True)  # la carpeta data/ siempre existe

import requests

import cvgen
import fetchers
import matcher
import tracker
from profile_store import load_profile, load_personas

STATE_PATH = "data/seen.json"
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def load_seen():
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return set(json.load(f).get("ids", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_seen(ids):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"ids": sorted(ids)}, f, ensure_ascii=False, indent=1)


def build_briefing(scored, seen, total):
    today = date.today().strftime("%d/%m/%Y")
    apply_now = [x for x in scored if x["band"] == "APPLY NOW"]
    apply = [x for x in scored if x["band"] == "APPLY"]
    review = [x for x in scored if x["band"] == "REVIEW"]
    new_ids = [x["id"] for x in scored[:12] if x["id"] not in seen]

    lines = [
        f"🦅 JOB INTELLIGENCE — {today}",
        f"Ofertas revisadas: {total} · Top: {len(apply_now)}🔥 {len(apply)}🟢 {len(review)}🟡",
        "",
    ]
    if apply_now:
        lines.append(f"🔥 EXCEPTIONAL ({len(apply_now)}) — APPLY NOW")
        for j in apply_now[:5]:
            lines.append(_offer_line(j, detail=True))
        lines.append("")
    if apply:
        lines.append(f"🟢 STRONG ({len(apply)}) — APPLY")
        for j in apply[:8]:
            lines.append(_offer_line(j))
        lines.append("")
    if review:
        lines.append(f"🟡 SECONDARY ({len(review)}) — REVIEW")
        for j in review[:6]:
            lines.append(_offer_line(j))
        lines.append("")
    if not apply_now and not apply:
        lines.append("Hoy no hay matches fuertes nuevos. Revisá las REVIEW manualmente.")
    return "\n".join(lines)


def _offer_line(j, detail=False):
    sal = f" · 💰 {j.get('salary') or ''}" if j.get("salary") else ""
    marker = j.get("salary_marker", {}).get("marker", "")
    line = (f"[{j['score']}/100 {j['emoji']}] {j['title']} — {j['company']} ({j['track_label']})"
            f"{sal} {marker}\n"
            f"  {j['url']}")
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


def main():
    print("🦅 Job Hunter — bot diario v2")
    profile = load_profile()
    keywords_ok = bool(profile.get("skills"))
    if not keywords_ok:
        print("⚠️  PERFIL DE EJEMPLO: cargá tu perfil real (data/profile.json).")
    print("Descargando ofertas…")
    jobs = fetchers.fetch_all()
    print(f"  {len(jobs)} ofertas únicas")

    scored = []
    for j in jobs:
        s = matcher.score_offer(j, profile)
        if s["band"] in ("APPLY NOW", "APPLY", "REVIEW"):
            s["id"] = j["id"]
            s.update({k: j[k] for k in ("title", "company", "url", "salary")})
            s["matched"] = matcher.family_match(j, profile)
            scored.append(s)
    order = {"APPLY NOW": 0, "APPLY": 1, "REVIEW": 2}
    scored.sort(key=lambda x: (order.get(x["band"], 9), -x["score"]))

    seen = load_seen()
    briefing = build_briefing(scored, seen, len(jobs))
    new_ids = [x["id"] for x in scored[:12] if x["id"] not in seen]
    seen.update(x["id"] for x in scored[:12])
    save_seen(seen)

    print("\n" + briefing + "\n")

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
                    zf.write(f["path"], os.path.join(pkg["offer_id"], f["name"]))
        print(f"📦 Paquetes del top 3 → {zip_path}")

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
