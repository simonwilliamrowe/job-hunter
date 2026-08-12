"""
Job Hunter - Servidor web (v2: scoring multi-carril + personas + tracker).
Arranque:  uvicorn app:app --host 0.0.0.0 --port 8000
"""
import json
import os
import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import ai
import applied as applied_mod
import cvgen
import fetchers
import matcher
import tracker as tracker_mod
from profile_store import load_profile, load_personas, save_profile, save_personas

DATA_DIR = "data"
CACHE_PATH = os.path.join(DATA_DIR, "jobs_cache.json")
GENERATED_DIR = "generated"
CACHE_TTL = 30 * 60

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)

app = FastAPI(title="Job Hunter")


def _load_cache():
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"ts": 0, "jobs": []}


def _save_cache(ts, jobs):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"ts": ts, "jobs": jobs}, f, ensure_ascii=False)


def _get_jobs(force=False):
    cache = _load_cache()
    if not force and time.time() - cache["ts"] < CACHE_TTL and cache["jobs"]:
        return cache["jobs"], cache["ts"]
    jobs = fetchers.fetch_all()
    ts = int(time.time())
    _save_cache(ts, jobs)
    return jobs, ts


def _enriched(jobs, profile):
    applied_ids = applied_mod.ids()
    out = []
    for j in jobs:
        if j["id"] in applied_ids:
            continue  # ya aplicaste: no se muestra nunca más
        s = matcher.score_offer(j, profile)
        s["matched"] = matcher.family_match(j, profile)
        out.append({
            "id": j["id"],
            "title": j["title"],
            "company": j["company"],
            "location": j["location"],
            "url": j["url"],
            "salary": j["salary"],
            "source": j["source"],
            "posted": j["posted"],
            "tags": j["tags"][:8],
            "score": s["score"],
            "band": s["band"],
            "emoji": s["emoji"],
            "track": s["track"],
            "track_label": s["track_label"],
            "persona": s["persona"],
            "salary_marker": s["salary_marker"]["marker"],
            "salary_label": s["salary_marker"]["label"],
            "reasons": s["reasons"],
            "matched": s["matched"],
        })
    order = {"APPLY NOW": 0, "APPLY": 1, "REVIEW": 2, "IGNORE": 3}
    out.sort(key=lambda j: (order.get(j["band"], 9), -j["score"]))
    return out


def _briefing(jobs_enriched, limit_top=3):
    """Briefing diario: grupos por banda + top oportunidades con por qué."""
    now = "ALTO" if jobs_enriched and jobs_enriched[0]["band"] == "APPLY NOW" else ""
    groups = {"APPLY NOW": [], "APPLY": [], "REVIEW": []}
    for j in jobs_enriched:
        if j["band"] in groups and len(groups[j["band"]]) < 10:
            groups[j["band"]].append(j)
    top = jobs_enriched[:limit_top]
    return {"groups": {k: v for k, v in groups.items()}, "top": top}


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/status")
def status():
    cache = _load_cache()
    return {"ai_enabled": ai.ai_enabled(), "cache_ts": cache["ts"],
            "cached_jobs": len(cache["jobs"]), "ttl_seconds": CACHE_TTL}


@app.get("/api/jobs")
def jobs(force: bool = False):
    profile = load_profile()
    jobs_raw, ts = _get_jobs(force=force)
    return {"ts": ts, "total": len(jobs_raw), "jobs": _enriched(jobs_raw, profile)}


@app.get("/api/briefing")
def briefing():
    profile = load_profile()
    jobs_raw, _ = _get_jobs()
    return _briefing(_enriched(jobs_raw, profile))


# ---------------------------- perfil y personas ----------------------------

@app.get("/api/profile")
def get_profile():
    return load_profile()


@app.put("/api/profile")
def put_profile(body: dict):
    p = load_profile()
    for k in ("name", "headline", "email", "phone", "location", "timezone", "links",
              "summary", "languages", "target_roles", "experience",
              "independent_experience", "education", "certifications", "achievements",
              "portfolio", "extra_keywords", "answers", "skills"):
        if k in body:
            p[k] = body[k]
    if isinstance(body.get("salary"), dict):
        sal = dict(p.get("salary", {}))
        for k, v in body["salary"].items():
            sal[k] = v
        p["salary"] = sal
    if isinstance(body.get("availability"), dict):
        av = dict(p.get("availability", {}))
        for k, v in body["availability"].items():
            av[k] = v
        p["availability"] = av
    save_profile(p)
    return {"ok": True, "profile": p}


@app.get("/api/personas")
def get_personas():
    return load_personas()


@app.put("/api/personas/{pid}")
def put_persona(pid: str, body: dict):
    personas = load_personas()
    if pid not in personas:
        raise HTTPException(404, "Persona no encontrada")
    for k in ("headline", "summary", "skills_order", "experience_order", "est_minutes", "label", "emoji"):
        if k in body:
            personas[pid][k] = body[k]
    save_personas(personas)
    return {"ok": True, "persona": personas[pid]}


# ---------------------------- paquetes ----------------------------

@app.post("/api/offer/{offer_id}/package")
def offer_package(offer_id: str, body: dict = None):
    track = (body or {}).get("track")
    profile = load_profile()
    jobs_raw, _ = _get_jobs()
    job = next((j for j in jobs_raw if j["id"] == offer_id), None)
    if not job:
        raise HTTPException(404, "Oferta no encontrada. Actualizá la lista.")
    pkg = cvgen.generate_package(profile, job, track=track, out_dir=GENERATED_DIR)
    pkg["files"] = [
        {"name": f["name"], "kind": f["kind"],
         "url": "/api/download/" + f["path"].split(GENERATED_DIR + os.sep, 1)[-1].replace(os.sep, "/")}
        for f in pkg["files"]
    ]
    pkg["offer"] = {"title": job["title"], "company": job["company"], "url": job["url"], "salary": job.get("salary")}
    return pkg


@app.get("/api/download/{file_path:path}")
def download(file_path: str):
    base = os.path.realpath(GENERATED_DIR)
    target = os.path.realpath(os.path.join(GENERATED_DIR, file_path))
    if not target.startswith(base) or not os.path.isfile(target):
        raise HTTPException(404, "Archivo no encontrado")
    return FileResponse(target, filename=os.path.basename(target))


# ---------------------------- tracker ----------------------------

@app.get("/api/applications")
def applications():
    return tracker_mod.load()


@app.post("/api/applications")
def applications_add(body: dict):
    return tracker_mod.add(
        company=body.get("company", ""),
        title=body.get("title", ""),
        url=body.get("url", ""),
        track=body.get("track", ""),
        persona=body.get("persona", ""),
        score=body.get("score"),
        band=body.get("band", ""),
        status=body.get("status", "Applied"),
        notes=body.get("notes", ""),
    )


@app.put("/api/applications/{app_id}")
def applications_update(app_id: str, body: dict):
    a = tracker_mod.update(app_id, body)
    if not a:
        raise HTTPException(404, "Aplicación no encontrada")
    return a


@app.get("/api/applications/stats")
def applications_stats():
    return tracker_mod.stats()


@app.get("/api/applied")
def get_applied():
    return applied_mod.load()


@app.post("/api/applied")
def add_applied(body: dict):
    items = applied_mod.add(
        offer_id=body.get("offer_id", ""),
        company=body.get("company", ""),
        title=body.get("title", ""),
        source=body.get("source", ""),
        snapshot=body.get("snapshot"),
    )
    return {"ok": True, "applied": items}


@app.delete("/api/applied/{offer_id}")
def remove_applied(offer_id: str):
    return {"ok": True, "applied": applied_mod.remove(offer_id)}


@app.get("/api/hot-keywords")
def hot_keywords():
    profile = load_profile()
    jobs_raw, _ = _get_jobs()
    keywords = matcher.build_keywords(profile)
    hot = matcher.hot_keywords(jobs_raw, top=40)
    missing = [k for k in hot if k not in keywords and not any(k in pk or pk in k for pk in keywords)]
    return {
        "hot": hot[:30],
        "missing": missing[:15],
        "advice": ("Si realmente manejás alguna keyword 'ausente', agregala a tu CV y LinkedIn. "
                   "Si NO la manejás, no la agregues. Keywords calientes = lo que más repiten "
                   "los anuncios activos."),
    }


app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
