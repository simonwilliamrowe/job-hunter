"""
Job Hunter - Módulo de descarga de ofertas desde APIs públicas de bolsas de
trabajo remoto. Sin scraping de LinkedIn: fuentes 100% legales y estables.

Fuentes: RemoteOK, Remotive, Jobicy, We Work Remotely, Arbeitnow, Python.org.
"""
import html
import re
import xml.etree.ElementTree as ET

import requests
from ats_boards import fetch_ats_boards

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}
TIMEOUT = 25


# ---------------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------------

def _clean_html(raw):
    """Convierte HTML sucio a texto plano legible."""
    if not raw:
        return ""
    raw = re.sub(r"<br\s*/?>", " ", raw, flags=re.I)
    raw = re.sub(r"<li[^>]*>", " • ", raw, flags=re.I)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw


def _norm(s):
    """Huella para deduplicar ofertas entre fuentes."""
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def _salary_str(min_v, max_v):
    try:
        lo = int(float(min_v or 0))
        hi = int(float(max_v or 0))
        if lo and hi:
            return f"${lo//1000}k - ${hi//1000}k"
        if lo:
            return f"${lo//1000}k"
        if hi:
            return f"${hi//1000}k"
    except (TypeError, ValueError):
        pass
    return ""


def _money_from_text(s):
    if not s or not str(s).strip():
        return ""
    s = str(s).strip()
    if s.lower() in ("unknown", "n/a", "tbd", "not disclosed"):
        return ""
    return s


def _parse_rss_items(content):
    root = ET.fromstring(content)
    return [it for it in root.iter("item")]


# ---------------------------------------------------------------------------
# RemoteOK (con filtro anti-spam: hoy mezclan listados basura)
# ---------------------------------------------------------------------------

ROLE_WORDS = (
    "developer", "engineer", "engineering", "software", "dev", "designer", "design",
    "product", "manager", "data", "analyst", "scientist", "support", "marketing",
    "sales", "growth", "content", "writer", "devops", "sysadmin", "admin",
    "recruiter", "finance", "ux", "ui", "qa", "tester", "architect", "lead",
    "head", "director", "intern", "junior", "senior", "full stack", "fullstack",
    "frontend", "front-end", "backend", "back-end", "mobile", "ios", "android",
    "security", "sre", "platform", "cloud", "ai", "ml", "machine learning",
    "wordpress", "shopify", "drupal", "rails", "python", "javascript", "typescript",
    "react", "vue", "angular", "node", "php", "java", "golang", "go ", "rust",
    "ruby", "kotlin", "swift", "c#", "c++", "scala", "elixir", "django", "flask",
    "fastapi", "laravel", "spring", "aws", "azure", "gcp", "kubernetes", "docker",
    "sql", "nosql", "postgres", "mysql", "mongo", "teacher", "instructor", "copywriter",
)

JUNK_TITLES = {"jobs", "job", "careers", "apply", "help", "staff", "driver",
               "how apply", "how to apply", "now hiring", "hiring"}


def _is_plausible_rok(j):
    """
    Filtro estricto anti-spam: RemoteOK sufre ataques de listados basura.
    Las ofertas legítimas publican salario; las de spam casi nunca.
    (Si RemoteOK limpia su API, se puede relajar este filtro.)
    """
    title = (j.get("position") or "").strip()
    if not title or title.lower() in JUNK_TITLES or len(title) < 3:
        return False
    try:
        sal = int(float(j.get("salary_min") or 0)) + int(float(j.get("salary_max") or 0))
    except (TypeError, ValueError):
        sal = 0
    return sal > 0


def fetch_remoteok():
    out = []
    try:
        r = requests.get("https://remoteok.com/api", headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            data = data[1:]  # el primer elemento es metadata
        for j in data:
            if not _is_plausible_rok(j):
                continue
            out.append({
                "id": f"rok-{j.get('id')}",
                "title": (j.get("position") or "").strip(),
                "company": (j.get("company") or "").strip(),
                "location": (j.get("location") or "").strip() or "Remote",
                "url": j.get("url") or f"https://remoteok.com/remote-jobs/{j.get('slug', '')}",
                "description": _clean_html(j.get("description")),
                "tags": [t for t in (j.get("tags") or []) if isinstance(t, str) and t],
                "salary": _salary_str(j.get("salary_min"), j.get("salary_max")),
                "source": "RemoteOK",
                "posted": str(j.get("date") or ""),
            })
    except Exception as e:  # noqa: BLE001
        print(f"[fetchers] RemoteOK error: {e}")
    return out


# ---------------------------------------------------------------------------
# Remotive
# ---------------------------------------------------------------------------

def fetch_remotive():
    out = []
    try:
        r = requests.get("https://remotive.com/api/remote-jobs", headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        for j in r.json().get("jobs", []):
            if not j.get("title"):
                continue
            out.append({
                "id": f"rem-{j.get('id')}",
                "title": j["title"].strip(),
                "company": (j.get("company_name") or "").strip(),
                "location": (j.get("candidate_required_location") or "").strip() or "Remote",
                "url": j.get("url") or "",
                "description": _clean_html(j.get("description")),
                "tags": [t for t in (j.get("tags") or []) if isinstance(t, str) and t],
                "salary": _money_from_text(j.get("salary")),
                "source": "Remotive",
                "posted": str(j.get("publication_date") or ""),
            })
    except Exception as e:  # noqa: BLE001
        print(f"[fetchers] Remotive error: {e}")
    return out


# ---------------------------------------------------------------------------
# Jobicy
# ---------------------------------------------------------------------------

def fetch_jobicy():
    out = []
    try:
        r = requests.get(
            "https://jobicy.com/api/v2/remote-jobs?count=100",
            headers=HEADERS, timeout=TIMEOUT,
        )
        r.raise_for_status()
        for j in r.json().get("jobs", []):
            title = j.get("jobTitle")
            if not title:
                continue
            industry = j.get("jobIndustry") or []
            if isinstance(industry, str):
                industry = [industry]
            out.append({
                "id": f"jcy-{j.get('id')}",
                "title": title.strip(),
                "company": (j.get("companyName") or "").strip(),
                "location": (j.get("jobGeo") or "").strip() or "Remote",
                "url": j.get("url") or "",
                "description": _clean_html(j.get("jobDescription")),
                "tags": [t for t in industry if isinstance(t, str) and t.strip()],
                "salary": _money_from_text(j.get("salary")),
                "source": "Jobicy",
                "posted": str(j.get("pubDate") or ""),
            })
    except Exception as e:  # noqa: BLE001
        print(f"[fetchers] Jobicy error: {e}")
    return out


# ---------------------------------------------------------------------------
# We Work Remotely (RSS)
# ---------------------------------------------------------------------------

WWR_FEEDS = {
    "All": "https://weworkremotely.com/remote-jobs.rss",
    "Programming": "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "DevOps/Sysadmin": "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
    "Design": "https://weworkremotely.com/categories/remote-design-jobs.rss",
    "Product": "https://weworkremotely.com/categories/remote-product-jobs.rss",
    "Customer Support": "https://weworkremotely.com/categories/remote-customer-support-jobs.rss",
}


def fetch_wwr():
    out = []
    seen = set()
    for label, url in WWR_FEEDS.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            for item in _parse_rss_items(r.content):
                title = (item.findtext("title") or "").strip()
                # formato actual: "Company: Job Title" (antes era "Job: Title at Company")
                if title.lower().startswith("job:"):
                    title_body = title[len("Job:"):].strip()
                    if " at " in title_body:
                        t, comp = title_body.rsplit(" at ", 1)
                    else:
                        t, comp = title_body, ""
                elif ": " in title:
                    comp, t = title.split(": ", 1)
                    comp, t = comp.strip(), t.strip()
                else:
                    t, comp = title, ""
                if not t:
                    continue
                fp = _norm(t + comp)
                if fp in seen:
                    continue
                seen.add(fp)
                out.append({
                    "id": f"wwr-{fp}",
                    "title": t.strip(),
                    "company": comp.strip(),
                    "location": "Remote",
                    "url": (item.findtext("link") or "").strip(),
                    "description": _clean_html(item.findtext("description")),
                    "tags": [label],
                    "salary": "",
                    "source": "WeWorkRemotely",
                    "posted": (item.findtext("pubDate") or "").strip(),
                })
        except Exception as e:  # noqa: BLE001
            print(f"[fetchers] WWR ({label}) error: {e}")
    return out


# ---------------------------------------------------------------------------
# Arbeitnow (remoto únicamente)
# ---------------------------------------------------------------------------

def fetch_arbeitnow():
    out = []
    for page in (1, 2):
        try:
            r = requests.get(
                f"https://www.arbeitnow.com/api/job-board-api?remote=true&page={page}",
                headers=HEADERS, timeout=TIMEOUT,
            )
            r.raise_for_status()
            for j in r.json().get("data", []):
                if not j.get("title") or not j.get("remote"):
                    continue
                out.append({
                    "id": f"arn-{j.get('slug')}",
                    "title": j["title"].strip(),
                    "company": (j.get("company_name") or "").strip(),
                    "location": (j.get("location") or "").strip() or "Remote",
                    "url": j.get("url") or f"https://www.arbeitnow.com/jobs/{j.get('slug')}",
                    "description": _clean_html(j.get("description")),
                    "tags": [t for t in (j.get("tags") or []) if isinstance(t, str) and t],
                    "salary": "",
                    "source": "Arbeitnow",
                    "posted": str(j.get("created_at") or ""),
                })
        except Exception as e:  # noqa: BLE001
            print(f"[fetchers] Arbeitnow error: {e}")
    return out


# ---------------------------------------------------------------------------
# Python.org Jobs (RSS, solo remotos)
# ---------------------------------------------------------------------------

def fetch_pythonjobs():
    out = []
    try:
        r = requests.get("https://www.python.org/jobs/feed/rss/", headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        for item in _parse_rss_items(r.content):
            title = (item.findtext("title") or "").strip()  # "Role, Company"
            desc = _clean_html(item.findtext("description"))
            if not title:
                continue
            if ", " in title:
                role, comp = title.rsplit(", ", 1)
            else:
                role, comp = title, ""
            low = f"{title} {desc}".lower()
            if "remote" not in low:
                continue  # solo ofertas remotas
            out.append({
                "id": f"pyj-{_norm(title)}",
                "title": role.strip(),
                "company": comp.strip(),
                "location": "Remote",
                "url": (item.findtext("link") or "").strip(),
                "description": desc,
                "tags": ["Python"],
                "salary": "",
                "source": "PythonJobs",
                "posted": (item.findtext("pubDate") or "").strip(),
            })
    except Exception as e:  # noqa: BLE001
        print(f"[fetchers] PythonJobs error: {e}")
    return out


# ---------------------------------------------------------------------------
# Himalayas (API pública con +100k ofertas; filtro remote)
# ---------------------------------------------------------------------------

def _cat_names(cats):
    names = []
    for c in cats or []:
        if isinstance(c, str):
            names.append(c)
        elif isinstance(c, dict):
            names.append(str(c.get("name") or c.get("title") or ""))
    return [n for n in names if n][:8]


def fetch_himalayas(pages=5, per_page=20):
    out = []
    # Himalayas bloquea User-Agents "de navegador" pero acepta uno simple
    hdr = {**HEADERS, "User-Agent": "Mozilla/5.0 (jobhunter)"}
    for offset in range(0, pages * per_page, per_page):
        try:
            r = requests.get(
                "https://himalayas.app/jobs/api",
                params={"remote": "true", "limit": per_page, "offset": offset},
                headers=hdr, timeout=TIMEOUT,
            )
            r.raise_for_status()
            jobs = r.json().get("jobs", [])
            if not jobs:
                break
            for j in jobs:
                title = j.get("title")
                if not title:
                    continue
                sal_parts = []
                mn, mx = j.get("minSalary"), j.get("maxSalary")
                cur = j.get("currency") or "USD"
                if mn and mx and str(mn) != str(mx):
                    sal_parts.append(f"{mn} - {mx} {cur}")
                elif mn:
                    sal_parts.append(f"{mn} {cur}")
                elif mx:
                    sal_parts.append(f"{mx} {cur}")
                if j.get("salaryPeriod"):
                    sal_parts.append(str(j["salaryPeriod"]))
                loc = j.get("locationRestrictions") or []
                loc_str = ", ".join(str(x) for x in loc[:4])
                if not loc_str:
                    loc_str = "Remote (worldwide)"
                out.append({
                    "id": f"him-{j.get('guid') or _norm(title + str(j.get('companyName', '')))}",
                    "title": title.strip(),
                    "company": (j.get("companyName") or "").strip(),
                    "location": loc_str,
                    "url": j.get("applicationLink") or j.get("guid") or "",
                    "description": _clean_html(j.get("description")),
                    "tags": _cat_names(j.get("categories")),
                    "salary": " ".join(sal_parts),
                    "source": "Himalayas",
                    "posted": str(j.get("pubDate") or ""),
                })
        except Exception as e:  # noqa: BLE001
            print(f"[fetchers] Himalayas error: {e}")
            break
    return out


# ---------------------------------------------------------------------------
# todo junto
# ---------------------------------------------------------------------------

def fetch_all():
    """Descarga todas las fuentes y deduplica por (empresa + puesto)."""
    raw = []
    for fn in (fetch_remoteok, fetch_remotive, fetch_jobicy, fetch_wwr,
               fetch_arbeitnow, fetch_pythonjobs, fetch_himalayas,
               fetch_ats_boards):
        raw.extend(fn())

    seen = set()
    deduped = []
    for j in raw:
        fp = _norm(j["company"] + j["title"])
        if fp in seen:
            continue
        seen.add(fp)
        if not j["description"] and not j["tags"]:
            continue
        deduped.append(j)
    return deduped


if __name__ == "__main__":
    import json
    jobs = fetch_all()
    print(f"Total ofertas únicas: {len(jobs)}")
    from collections import Counter
    for src, n in Counter(j["source"] for j in jobs).items():
        print(f"  {src}: {n}")
