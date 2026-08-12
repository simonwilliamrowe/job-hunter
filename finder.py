"""
Job Hunter - Buscador de oferta exacta por texto (email de la empresa).

Cuando el candidato recibe un email de entrevista, pasamos el texto (o la
empresa + puesto) y localizamos la oferta exacta en la caché para poder
preparar la entrevista con los requisitos reales.
"""
import json
import re

CACHE = "data/jobs_cache.json"
APPLIED = "data/applied.json"


def load_cache():
    try:
        with open(CACHE, "r", encoding="utf-8") as f:
            return json.load(f).get("jobs", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _norm(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _tokenize(s):
    return set(_norm(s).split())


def load_applied():
    """Las ofertas a las que ya aplicaste (archivo PERMANENTE con snapshot)."""
    try:
        with open(APPLIED, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def find_offer(text, top=3):
    """
    Dado el texto del email (o empresa + puesto), devuelve las ofertas que
    mejor coinciden. Busca PRIMERO en las APLICADAS (archivo permanente con
    snapshot exacto) y luego en la caché de ofertas recientes.
    """
    if not text:
        return []
    # 1) aplicadas (la garantía: oferta exacta, aunque hayan pasado meses)
    applied = load_applied()
    from_a = _match_in(text, applied)
    if from_a:
        return [x["snapshot"] if x.get("snapshot") else x for x in from_a[:top]]
    # 2) caché reciente
    jobs = load_cache()
    return _match_in(text, jobs)[:top]


def _match_in(text, jobs):
    q = _tokenize(text)
    stop = set("interview interview invitation congratulations selected shortlisted "
               "hello dear thank thanks pleased excited opportunity role position job "
               "company team we are would like to schedule call zoom meeting next week "
               "please let me know availability time date application applied candidate "
               "hiring manager recruitment".split())
    q = q - stop
    scored = []
    for j in jobs:
        hay = _norm(f"{j.get('company', '')} {j.get('title', '')} {j.get('source', '')}")
        company_tokens = set(_norm(j.get('company', '')).split())
        inter = q & company_tokens
        score = len(inter) * 10
        title_tokens = set(_norm(j.get('title', '')).split())
        score += len(q & title_tokens) * 2
        if score > 0:
            scored.append((score, j))
    scored.sort(key=lambda x: -x[0])
    return [j for _, j in scored]
    q = _tokenize(text)
    # quitar palabras genéricas
    stop = set("interview interview invitation congratulations selected shortlisted "
               "hello dear thank thanks pleased excited opportunity role position job "
               "company team we are would like to schedule call zoom meeting next week "
               "please let me know availability time date application applied candidate "
               "hiring manager recruitment".split())
    q = q - stop

    scored = []
    for j in jobs:
        hay = _norm(f"{j.get('company', '')} {j.get('title', '')} {j.get('source', '')}")
        hay_tokens = set(hay.split())
        # empresas: coincidencia de palabra completa (lo más fiable)
        company_tokens = set(_norm(j.get('company', '')).split())
        inter = q & company_tokens
        score = len(inter) * 10
        # título: coincidencias parciales
        title_tokens = set(_norm(j.get('title', '')).split())
        score += len(q & title_tokens) * 2
        if score > 0:
            scored.append((score, j))
    scored.sort(key=lambda x: -x[0])
    return [j for _, j in scored[:top]]


def format_offer(j):
    return (
        f"🎯 {j.get('title', '')}\n"
        f"   Empresa: {j.get('company', '')} | Fuente: {j.get('source', '')}\n"
        f"   Ubicación: {j.get('location', '')}\n"
        f"   Salario: {j.get('salary') or 'no publicado'}\n"
        f"   Link: {j.get('url', '')}\n"
        f"   Tags: {', '.join((j.get('tags') or [])[:6])}"
    )


def extract_company(text):
    """Intenta sacar el nombre de la empresa del email (línea de firma, remitente)."""
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    for l in lines:
        l2 = l.strip()
        # firmas típicas: "Best regards,\nName\nCompany"
        if l2 and not re.match(r"^(hi|hello|dear|best|regards|thanks|thank|cheers|sincerely)", l2, re.I) \
           and len(l2) > 2 and len(l2) < 40 and " " in l2:
            return l2
    return ""
