"""Job Hunter - Fetchers.

Pipeline de descarga de ofertas. Modular, con rate limiting por host,
deduplicación y normalización.

Fuentes:
  - 7 job boards públicos (RemoteOK, Remotive, Jobicy, WWR, Arbeitnow, CryptoJobs, Web3Career)
  - 30+ empresas vía ATS (Greenhouse, Lever, Ashby, Workable)
  - LinkedIn Guest API opcional (~120 queries LATAM, off por default)
"""

import html
import json
import re
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from urllib.parse import urlparse

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}
TIMEOUT = 25

RATE_LIMITS = {
    "www.linkedin.com": 1.0,
    "boards-api.greenhouse.io": 2.0,
    "api.lever.co": 2.0,
    "jobs.ashbyhq.com": 1.0,
    "api.smartrecruiters.com": 2.0,
    "api.recruitee.com": 2.0,
    "apply.workable.com": 2.0,
    "default": 1.0,
}


def _clean_html(raw):
    if not raw:
        return ""
    raw = re.sub(r"<br\s*/?>", " ", raw, flags=re.I)
    raw = re.sub(r"<li[^>]*>", " • ", raw, flags=re.I)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw


def _norm(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def _host_rate(url):
    host = urlparse(url).netloc
    return RATE_LIMITS.get(host, RATE_LIMITS["default"])


_LAST_FETCH = defaultdict(float)


def _throttle(url):
    rate = _host_rate(url)
    elapsed = time.time() - _LAST_FETCH[urlparse(url).netloc]
    if elapsed < 1 / rate:
        time.sleep((1 / rate) - elapsed)
    _LAST_FETCH[urlparse(url).netloc] = time.time()


def _get(url, **kwargs):
    _throttle(url)
    for attempt in range(2):
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, **kwargs)
            if r.status_code == 429:
                time.sleep(120)
                continue
            return r
        except requests.RequestException:
            time.sleep(5)
    return None


# ============================================================================
# Fetchers: job boards
# ============================================================================

def fetch_remoteok():
    r = _get("https://remoteok.com/api")
    if not r or r.status_code != 200:
        return []
    try:
        data = r.json()
    except Exception:
        return []
    out = []
    for j in data[1:]:
        out.append({
            "id": f"rok-{j.get('id','')}",
            "title": j.get("position", ""),
            "company": j.get("company", ""),
            "location": j.get("location", "Remote"),
            "description": " ".join((j.get("description", "") or "").split()[:300]),
            "tags": j.get("tags", []),
            "url": j.get("url", ""),
            "source": "RemoteOK",
            "salary": j.get("salary", "") or "",
        })
    return out


def fetch_remotive(category=None):
    url = "https://remotive.com/api/remote-jobs?limit=100"
    if category:
        url += f"&category={category}"
    r = _get(url)
    if not r or r.status_code != 200:
        return []
    try:
        data = r.json()
    except Exception:
        return []
    out = []
    for j in data.get("jobs", []):
        out.append({
            "id": f"rem-{j.get('id','')}",
            "title": j.get("title", ""),
            "company": j.get("company_name", ""),
            "location": j.get("candidate_required_location", "Worldwide"),
            "description": j.get("description", ""),
            "tags": j.get("tags", []),
            "url": j.get("url", ""),
            "source": "Remotive",
            "salary": j.get("salary", "") or "",
        })
    return out


def fetch_jobicy():
    r = _get("https://jobicy.com/api/v2/remote-jobs?count=50")
    if not r or r.status_code != 200:
        return []
    try:
        data = r.json()
    except Exception:
        return []
    out = []
    for j in data.get("jobList", []):
        out.append({
            "id": f"jcy-{j.get('id','')}",
            "title": j.get("jobTitle", ""),
            "company": j.get("companyName", ""),
            "location": j.get("jobGeo", "Remote"),
            "description": j.get("jobDescription", ""),
            "tags": [j.get("jobIndustry", "")] if j.get("jobIndustry") else [],
            "url": j.get("url", ""),
            "source": "Jobicy",
            "salary": "",
        })
    return out


def fetch_wwr():
    feeds = [
        "https://weworkremotely.com/categories/remote-customer-support-jobs.rss",
        "https://weworkremotely.com/categories/remote-sales-and-marketing-jobs.rss",
    ]
    out = []
    for url in feeds:
        r = _get(url)
        if not r or r.status_code != 200:
            continue
        try:
            root = ET.fromstring(r.content)
        except Exception:
            continue
        for item in root.findall(".//item"):
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            desc = item.findtext("description", "")
            company = ""
            if " at " in title:
                company = title.split(" at ")[-1].split(":")[0].strip()
            out.append({
                "id": f"wwr-{link.split('/')[-1] if link else title}",
                "title": title,
                "company": company,
                "location": "Remote",
                "description": _clean_html(desc),
                "tags": [],
                "url": link,
                "source": "WeWorkRemotely",
                "salary": "",
            })
    return out


def fetch_arbeitnow():
    r = _get("https://www.arbeitnow.com/api/job-board-api?remote=true")
    if not r or r.status_code != 200:
        return []
    try:
        data = r.json()
    except Exception:
        return []
    out = []
    for j in data.get("data", []):
        out.append({
            "id": f"arn-{j.get('slug','')}",
            "title": j.get("title", ""),
            "company": j.get("company_name", ""),
            "location": "Remote",
            "description": j.get("description", ""),
            "tags": j.get("tags", []),
            "url": j.get("url", ""),
            "source": "Arbeitnow",
            "salary": j.get("salary", "") or "",
        })
    return out


def fetch_cryptocurrencyjobs():
    r = _get("https://cryptocurrencyjobs.co/index.xml")
    if not r or r.status_code != 200:
        return []
    try:
        root = ET.fromstring(r.content)
    except Exception:
        return []
    out = []
    for item in root.findall(".//item"):
        title = item.findtext("title", "")
        link = item.findtext("link", "")
        desc = item.findtext("description", "")
        company = ""
        if " at " in title:
            company = title.split(" at ")[-1].strip()
        out.append({
            "id": f"ccj-{link.split('/')[-1] if link else title}",
            "title": title,
            "company": company,
            "location": "",
            "description": _clean_html(desc),
            "tags": [],
            "url": link,
            "source": "CryptocurrencyJobs",
            "salary": "",
        })
    return out


def fetch_web3career():
    r = _get("https://web3.career/")
    if not r or r.status_code != 200:
        return []
    ld_blocks = re.findall(r'<script type="application/ld\+json">(.+?)</script>', r.text, re.S)
    out = []
    seen = set()
    for block in ld_blocks:
        try:
            data = json.loads(block)
        except Exception:
            continue
        items = []
        if isinstance(data, dict) and "@graph" in data:
            items = [g for g in data["@graph"] if isinstance(g, dict) and g.get("@type") == "JobPosting"]
        elif isinstance(data, list):
            items = [g for g in data if isinstance(g, dict) and g.get("@type") == "JobPosting"]
        elif isinstance(data, dict) and data.get("@type") == "JobPosting":
            items = [data]
        for it in items:
            title = it.get("title", "")
            org = it.get("hiringOrganization", {})
            company = org.get("name", "") if isinstance(org, dict) else str(org)
            loc_obj = it.get("jobLocation", {})
            location = ""
            if isinstance(loc_obj, dict):
                addr = loc_obj.get("address", {})
                if isinstance(addr, dict):
                    location = addr.get("addressLocality", "") or addr.get("addressCountry", "")
            url = it.get("url", "") or it.get("@id", "") or ""
            desc = _clean_html(it.get("description", "") or "")
            fp = (title, company)
            if fp in seen:
                continue
            seen.add(fp)
            out.append({
                "id": f"w3c-{url.split('/')[-1] if url else title}",
                "title": title,
                "company": company,
                "location": location,
                "description": desc,
                "tags": [],
                "url": url,
                "source": "Web3Career",
                "salary": "",
            })
    return out


# ============================================================================
# Fetchers ATS (Greenhouse, Lever, Ashby, Workable)
# ============================================================================

def _normalize_ats_job(j, source, ats_name):
    if not j.get("title"):
        return None
    url = j.get("url") or j.get("absolute_url") or j.get("apply_url") or j.get("hostedUrl") or ""
    if not url:
        return None
    loc = j.get("location", "")
    if isinstance(loc, dict):
        loc = loc.get("name", "")
    desc = j.get("description") or j.get("content") or ""
    if isinstance(desc, str) and "<" in desc:
        desc = _clean_html(desc)
    elif isinstance(desc, str):
        desc = desc[:7000]
    salary = ""
    for k in ("salary", "salary_range", "compensation"):
        v = j.get(k)
        if v:
            if isinstance(v, dict):
                salary = v.get("value", "") or f"{v.get('min', '')}-{v.get('max', '')}"
            else:
                salary = str(v)
            break
    dept = ""
    if j.get("departments"):
        if isinstance(j["departments"], list) and j["departments"]:
            dept = j["departments"][0].get("name", "")
    tags = []
    if j.get("tags"):
        tags = j["tags"] if isinstance(j["tags"], list) else []
    if dept:
        tags.append(dept)
    return {
        "id": f"{ats_name.lower()}-{j.get('id', url.split('/')[-1])}",
        "title": j.get("title", ""),
        "company": source,
        "location": loc,
        "description": desc,
        "tags": tags,
        "url": url,
        "source": ats_name,
        "salary": salary,
    }


def fetch_greenhouse(board, company_name=None):
    company_name = company_name or board.title()
    r = _get(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true")
    if not r or r.status_code != 200:
        return []
    try:
        data = r.json()
    except Exception:
        return []
    out = []
    for j in data.get("jobs", []):
        norm = _normalize_ats_job(j, company_name, f"GH-{board}")
        if norm:
            out.append(norm)
    return out


def fetch_lever(company, company_name=None):
    company_name = company_name or company.title()
    r = _get(f"https://api.lever.co/v0/postings/{company}?mode=json")
    if not r or r.status_code != 200:
        return []
    try:
        data = r.json()
    except Exception:
        return []
    out = []
    for j in data:
        norm = _normalize_ats_job({
            "id": j.get("id"),
            "title": j.get("text", ""),
            "url": j.get("hostedUrl") or j.get("applyUrl", ""),
            "location": j.get("categories", {}).get("location", ""),
            "description": _clean_html(j.get("description", "")),
            "tags": list(j.get("categories", {}).values()) if j.get("categories") else [],
            "department": j.get("categories", {}).get("team", ""),
        }, company_name, f"LV-{company}")
        if norm:
            out.append(norm)
    return out


def fetch_ashby(company, company_name=None):
    company_name = company_name or company.title()
    r = _get(f"https://jobs.ashbyhq.com/{company}/jobs")
    if not r or r.status_code != 200:
        return []
    try:
        data = r.json()
    except Exception:
        return []
    out = []
    for j in data.get("jobs", []):
        norm = _normalize_ats_job({
            "id": j.get("id"),
            "title": j.get("title", ""),
            "url": f"https://jobs.ashbyhq.com/{company}/{j.get('id','')}",
            "location": j.get("location", ""),
            "description": j.get("descriptionHtml", "") or j.get("description", ""),
            "department": j.get("department", ""),
        }, company_name, f"ASH-{company}")
        if norm:
            out.append(norm)
    return out


def fetch_workable(company, company_name=None):
    company_name = company_name or company.title()
    r = _get(f"https://apply.workable.com/api/v1/widget/accounts/{company}")
    if not r or r.status_code != 200:
        return []
    try:
        data = r.json()
    except Exception:
        return []
    out = []
    for j in data.get("jobs", []):
        norm = _normalize_ats_job({
            "id": j.get("shortcode") or j.get("id"),
            "title": j.get("title", ""),
            "url": j.get("url") or f"https://apply.workable.com/{company}/j/{j.get('shortcode','')}",
            "location": j.get("location", {}).get("city", "") if isinstance(j.get("location"), dict) else j.get("location", ""),
            "description": _clean_html(j.get("description", "")),
            "department": j.get("department", ""),
        }, company_name, f"WB-{company}")
        if norm:
            out.append(norm)
    return out


# ============================================================================
# Listas de boards ATS
# ============================================================================

GREENHOUSE_BOARDS = [
    ("coinbase", "Coinbase"),
    ("kraken", "Kraken"),
    ("gemini", "Gemini"),
    ("binance", "Binance"),
    ("crypto", "Crypto.com"),
    ("okx", "OKX"),
    ("blockchain", "Blockchain.com"),
    ("chainalysis", "Chainalysis"),
    ("fireblocks", "Fireblocks"),
    ("circle", "Circle"),
    ("consensys", "ConsenSys"),
    ("opensea", "OpenSea"),
    ("ramp", "Ramp"),
    ("brex", "Brex"),
    ("deel", "Deel"),
    ("remote", "Remote"),
    ("invisible-technologies", "Invisible Technologies"),
    ("gitlab", "GitLab"),
    ("datadog", "Datadog"),
    ("snyk", "Snyk"),
    ("dropbox", "Dropbox"),
    ("twilio", "Twilio"),
    ("github", "GitHub"),
    ("elastic", "Elastic"),
    ("intercom", "Intercom"),
    ("notion", "Notion"),
    ("miro", "Miro"),
    ("stripe", "Stripe"),
    ("wise", "Wise"),
    ("dlocal", "dLocal"),
]

LEVER_BOARDS = [
    ("kraken", "Kraken"),
    ("bitso", "Bitso"),
    ("ripio", "Ripio"),
    ("lemon", "Lemon"),
    ("buenbit", "Buenbit"),
    ("bitrefill", "Bitrefill"),
    ("bitwage", "Bitwage"),
    ("paxful", "Paxful"),
    ("keyrock", "Keyrock"),
    ("wintermute", "Wintermute"),
    ("modulr", "Modulr"),
    ("rain", "Rain"),
    ("meru", "Meru"),
    ("partnerhero", "PartnerHero"),
    ("modsquad", "ModSquad"),
    ("taskus", "TaskUs"),
    ("5ca", "5CA"),
    ("boldr", "Boldr"),
    ("oyster", "Oyster"),
    ("toptal", "Toptal"),
    ("automattic", "Automattic"),
    ("canonical", "Canonical"),
    ("buffer", "Buffer"),
    ("hotjar", "Hotjar"),
    ("safetywing", "SafetyWing"),
    ("supercr", "Superside"),
]

ASHBY_BOARDS = [
    ("supportyourapp", "SupportYourApp"),
    ("modulr-finance", "Modulr Finance"),
    ("linear", "Linear"),
    ("ramp", "Ramp"),
    ("vanta", "Vanta"),
    ("mercury", "Mercury"),
    ("gusto", "Gusto"),
    ("watershed", "Watershed"),
    ("maven", "Maven"),
    ("retool", "Retool"),
    ("scaleai", "Scale AI"),
]

WORKABLE_BOARDS = [
    ("tdcx", "TDCX"),
    ("peaksupport", "Peak Support"),
    ("vee", "Vee"),
    ("cloudtask", "CloudTask"),
    ("meru", "Meru"),
    ("messagebird", "MessageBird"),
    ("bitso", "Bitso"),
]


def fetch_ats_boards():
    """Descarga todas las ATS configuradas."""
    out = []
    for board, name in GREENHOUSE_BOARDS:
        try:
            jobs = fetch_greenhouse(board, name)
            if jobs:
                out.extend(jobs)
        except Exception as e:
            print(f"[ats] GH {board} error: {e}")
    for board, name in LEVER_BOARDS:
        try:
            jobs = fetch_lever(board, name)
            if jobs:
                out.extend(jobs)
        except Exception as e:
            print(f"[ats] LV {board} error: {e}")
    for board, name in ASHBY_BOARDS:
        try:
            jobs = fetch_ashby(board, name)
            if jobs:
                out.extend(jobs)
        except Exception as e:
            print(f"[ats] ASH {board} error: {e}")
    for board, name in WORKABLE_BOARDS:
        try:
            jobs = fetch_workable(board, name)
            if jobs:
                out.extend(jobs)
        except Exception as e:
            print(f"[ats] WB {board} error: {e}")
    return out


# ============================================================================
# LinkedIn Guest API (queries LATAM-focused, bilingüe ES/EN)
# ============================================================================

_LINKEDIN_QUERIES = [
    # Customer service / support / care / success (EN, global)
    ("customer service", "Latin America"),
    ("customer service", "Mexico"),
    ("customer service", "Colombia"),
    ("customer service", "Argentina"),
    ("customer service", "Chile"),
    ("customer service", "Peru"),
    ("customer service", "Brazil"),
    ("customer support", "Latin America"),
    ("customer support", "Mexico"),
    ("customer support", "Colombia"),
    ("customer support", "Argentina"),
    ("customer care", "Latin America"),
    ("customer care", "Mexico"),
    ("customer success", "Latin America"),
    ("customer success", "Mexico"),
    ("client support", "Latin America"),
    ("client services", "Latin America"),
    # Soporte en ESPAÑOL
    ("soporte al cliente", "Latin America"),
    ("soporte al cliente", "Mexico"),
    ("soporte al cliente", "Colombia"),
    ("atención al cliente", "Latin America"),
    ("atención al cliente", "Mexico"),
    ("atención al cliente", "Colombia"),
    ("servicio al cliente", "Latin America"),
    ("servicio al cliente", "Mexico"),
    ("servicio al cliente", "Argentina"),
    ("asistente de soporte", "Latin America"),
    # Chat / live chat / help desk
    ("chat support", "Latin America"),
    ("chat support", "Mexico"),
    ("live chat", "Latin America"),
    ("help desk", "Latin America"),
    ("technical support", "Latin America"),
    ("technical support", "Mexico"),
    ("soporte técnico", "Latin America"),
    ("soporte técnico", "Mexico"),
    # Community / moderación
    ("community manager", "Latin America"),
    ("community moderator", "Latin America"),
    ("moderador de comunidad", "Latin America"),
    ("gestor de comunidad", "Latin America"),
    # Operations
    ("operations", "Latin America"),
    ("operations associate", "Latin America"),
    ("operaciones", "Latin America"),
    ("asistente de operaciones", "Latin America"),
    # Bilingüe
    ("bilingual customer service", "Latin America"),
    ("bilingual customer service", "Mexico"),
    ("spanish customer service", "Latin America"),
    ("spanish customer support", "Latin America"),
    ("bilingual support", "Latin America"),
    ("atención bilingüe", "Latin America"),
    # Crypto
    ("crypto support", "Latin America"),
    ("crypto customer service", "Latin America"),
    ("web3 community", "Latin America"),
    ("crypto operations", "Latin America"),
    ("soporte crypto", "Latin America"),
    # AI
    ("ai trainer", "Latin America"),
    ("ai trainer", "Mexico"),
    ("ai tutor", "Latin America"),
    ("data annotator", "Latin America"),
    ("data annotator", "Mexico"),
    ("prompt engineer", "Latin America"),
    ("entrenador de IA", "Latin America"),
    # VA
    ("virtual assistant", "Latin America"),
    ("virtual assistant", "Mexico"),
    ("data entry", "Latin America"),
    ("asistente virtual", "Latin America"),
    ("capturista de datos", "Mexico"),
    # Content
    ("content writer", "Latin America"),
    ("copywriter", "Latin America"),
    ("redactor", "Latin America"),
    ("escritor de contenido", "Latin America"),
    # Trust & Safety
    ("trust and safety", "Latin America"),
    ("risk analyst", "Latin America"),
    ("compliance analyst", "Latin America"),
    ("kyc analyst", "Latin America"),
    ("fraud analyst", "Latin America"),
    ("analista de cumplimiento", "Latin America"),
    # Trading
    ("junior trader", "Latin America"),
    ("trading analyst", "Latin America"),
    # Sales
    ("inbound sales", "Latin America"),
    ("account executive", "Latin America"),
    ("fintech", "Latin America"),
    # Ubicaciones específicas
    ("customer support", "Bogota"),
    ("customer support", "Lima"),
    ("customer support", "Buenos Aires"),
    ("customer support", "Santiago"),
    ("customer support", "CDMX"),
    ("customer support", "Quito"),
    ("customer support", "San Jose"),
    ("customer support", "Asuncion"),
    ("virtual assistant", "Bogota"),
    ("virtual assistant", "CDMX"),
    ("virtual assistant", "Lima"),
    ("data entry", "Mexico City"),
    ("data entry", "Buenos Aires"),
    # Remote global
    ("remote LATAM", ""),
    ("remote South America", ""),
    ("remoto LATAM", ""),
]


def fetch_linkedin_latam():
    """LinkedIn Guest API: ~120 queries LATAM-focused. Solo pasamos el link."""
    out = []
    seen_ids = set()
    for kw, loc in _LINKEDIN_QUERIES:
        try:
            params = {"keywords": kw, "f_WT": "2"}
            if loc:
                params["location"] = loc
            r = _get(
                "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search",
                params=params,
            )
            if not r or r.status_code != 200:
                continue
            titles = re.findall(
                r'<h3[^>]*class="base-search-card__title"[^>]*>([^<]+)</h3>', r.text)
            companies = re.findall(
                r'<h4[^>]*class="base-search-card__subtitle"[^>]*>\s*<a[^>]*>([^<]+)</a>', r.text)
            locations = re.findall(
                r'<span class="job-search-card__location"[^>]*>([^<]+)</span>', r.text)
            links = re.findall(
                r'<a class="base-card__full-link[^"]*"[^>]*href="([^"]+)"', r.text)
            n = min(len(titles), len(companies), len(locations), len(links))
            for i in range(n):
                oid_m = re.search(r"/view/(\d+)", links[i])
                oid = oid_m.group(1) if oid_m else links[i]
                if oid in seen_ids:
                    continue
                seen_ids.add(oid)
                out.append({
                    "id": f"li-{oid}",
                    "title": titles[i].strip(),
                    "company": companies[i].strip(),
                    "location": locations[i].strip(),
                    "description": "",
                    "tags": [],
                    "url": links[i],
                    "source": "LinkedIn",
                    "salary": "",
                })
        except Exception as e:
            print(f"[linkedin {kw}/{loc}] error: {e}")
    return out


# ============================================================================
# Deduplicación y orquestación
# ============================================================================

def _dedupe(jobs):
    seen = set()
    out = []
    for j in jobs:
        fp = _norm(j.get("company", "") + j.get("title", ""))
        if fp in seen:
            continue
        seen.add(fp)
        if not j.get("description") and not j.get("tags"):
            continue
        out.append(j)
    return out


def fetch_all(include_linkedin=False, include_ats=True):
    """Descarga todas las fuentes."""
    out = []
    for fn in (fetch_remoteok, fetch_remotive, fetch_jobicy, fetch_wwr,
               fetch_arbeitnow, fetch_cryptocurrencyjobs, fetch_web3career):
        try:
            jobs = fn()
            if jobs:
                out.extend(jobs)
        except Exception as e:
            print(f"[fetchers] {fn.__name__} error: {e}")
    if include_ats:
        try:
            jobs = fetch_ats_boards()
            if jobs:
                out.extend(jobs)
        except Exception as e:
            print(f"[fetchers] ats error: {e}")
    if include_linkedin:
        try:
            jobs = fetch_linkedin_latam()
            if jobs:
                out.extend(jobs)
        except Exception as e:
            print(f"[fetchers] linkedin error: {e}")
    return _dedupe(out)


if __name__ == "__main__":
    import sys
    include_li = "--linkedin" in sys.argv
    jobs = fetch_all(include_linkedin=include_li, include_ats=True)
    print(f"Total ofertas únicas: {len(jobs)}")
    from collections import Counter
    for src, n in sorted(Counter(j["source"] for j in jobs).items()):
        print(f"  {src}: {n}")
