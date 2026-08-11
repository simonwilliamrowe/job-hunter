"""
Job Hunter - Fuente ATS-boards: vacantes públicas de empresas crypto/fintech
que usan Greenhouse, Lever o Ashby. Verificado en vivo el 10/08/2026.

Estas APIs son públicas y oficiales (diseñadas para consumo abierto).
Se filtran roles relevantes (support / community / ops / research / fintech)
y se descartan los puramente de ingeniería, para mantener el corpus útil.
"""
import re

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (jobhunter)"}
TIMEOUT = 25

# boards verificados (empresa -> slug del board)
BOARDS = {
    "greenhouse": {
        "coinbase": "Coinbase", "gemini": "Gemini", "ripple": "Ripple",
        "fireblocks": "Fireblocks",
        "monzo": "Monzo", "n26": "N26", "bitso": "Bitso (LATAM)",
    },
    "lever": {
        "ledger": "Ledger", "moonpay": "MoonPay", "binance": "Binance",
        "plaid": "Plaid",
    },
    "ashby": {
        "kraken": "Kraken",
    },
}

ROLE_RX = re.compile(
    r"\b(support|customer (success|experience|service)|helpdesk|help desk|ticket|"
    r"community|moderat|operations|ops\b|research|analyst|due diligence|tokenomics|"
    r"compliance|kyc|aml|fraud|risk|trust & safety|payments|payment|onboarding|"
    r"troubleshoot|escalation|account manager|client (success|support|service)|"
    r"back[- ]office|administrative|quality assurance|cx\b|fintech|financial|"
    r"blockchain|crypto|wallet|web3|defi|exchange|operations associate)\b",
    re.I,
)
REMOTE_RX = re.compile(r"\b(remote|worldwide|anywhere|distributed)\b", re.I)


def _clean_html(raw):
    if not raw:
        return ""
    raw = re.sub(r"<br\s*/?>", " ", raw, flags=re.I)
    raw = re.sub(r"<li[^>]*>", " • ", raw, flags=re.I)
    raw = re.sub(r"<[^>]+>", " ", raw)
    import html
    raw = html.unescape(raw)
    return re.sub(r"\s+", " ", raw).strip()


def _norm(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def _keep(job_title, desc):
    hay = f"{job_title} {(desc or '')[:800]}"
    return bool(ROLE_RX.search(hay))


def fetch_greenhouse():
    out = []
    for slug, label in BOARDS["greenhouse"].items():
        try:
            r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
                             headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            for j in r.json().get("jobs", []):
                title = j.get("title") or ""
                desc = _clean_html(j.get("content"))
                loc = ", ".join(str(x) for x in (j.get("location") or {}).values() if x)
                if not _keep(title, desc):
                    continue
                if not REMOTE_RX.search(f"{title} {loc} {desc[:500]}"):
                    continue
                sal = ""
                if j.get("compensation"):
                    c = j["compensation"]
                    if c.get("min") or c.get("max"):
                        sal = f"{c.get('min','')} - {c.get('max','')} {c.get('currency','USD')} ({c.get('period','yearly')})"
                out.append({
                    "id": f"gh-{slug}-{j.get('id')}",
                    "title": title.strip(),
                    "company": label,
                    "location": loc or "Remote",
                    "url": j.get("absolute_url") or f"https://boards.greenhouse.io/{slug}/jobs/{j.get('id')}",
                    "description": desc,
                    "tags": [label, "Greenhouse"],
                    "salary": sal,
                    "source": "Greenhouse",
                    "posted": str(j.get("updated_at") or ""),
                })
        except Exception as e:  # noqa: BLE001
            print(f"[ats] Greenhouse {slug}: {e}")
    return out


def fetch_lever():
    out = []
    for slug, label in BOARDS["lever"].items():
        try:
            r = requests.get(f"https://api.lever.co/v0/postings/{slug}?mode=json",
                             headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            for j in r.json():
                title = j.get("text") or ""
                desc = _clean_html(j.get("description"))
                loc = j.get("categories", {}).get("location") or "Remote"
                if not _keep(title, desc):
                    continue
                if not REMOTE_RX.search(f"{title} {loc} {desc[:500]}"):
                    continue
                sal = ""
                if j.get("salaryRange"):
                    s = j["salaryRange"]
                    if s.get("min") or s.get("max"):
                        sal = f"{s.get('min','')} - {s.get('max','')} {s.get('currency','USD')}"
                out.append({
                    "id": f"lv-{slug}-{j.get('id')}",
                    "title": title.strip(),
                    "company": label,
                    "location": loc,
                    "url": j.get("hostedUrl") or j.get("applyUrl") or "",
                    "description": desc,
                    "tags": [label, "Lever"],
                    "salary": sal,
                    "source": "Lever",
                    "posted": str(j.get("createdAt") or ""),
                })
        except Exception as e:  # noqa: BLE001
            print(f"[ats] Lever {slug}: {e}")
    return out


def fetch_ashby():
    out = []
    for slug, label in BOARDS["ashby"].items():
        try:
            r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
                             headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            for j in r.json().get("jobs", []):
                title = j.get("title") or ""
                desc = _clean_html(j.get("descriptionHtml") or j.get("descriptionPlain"))
                loc = j.get("location") or "Remote"
                if not _keep(title, desc):
                    continue
                if not REMOTE_RX.search(f"{title} {loc} {desc[:500]}"):
                    continue
                out.append({
                    "id": f"ab-{slug}-{j.get('id')}",
                    "title": title.strip(),
                    "company": label,
                    "location": loc,
                    "url": j.get("jobUrl") or "",
                    "description": desc,
                    "tags": [label, "Ashby"],
                    "salary": "",
                    "source": "Ashby",
                    "posted": str(j.get("publishedAt") or ""),
                })
        except Exception as e:  # noqa: BLE001
            print(f"[ats] Ashby {slug}: {e}")
    return out


def fetch_ats_boards():
    raw = fetch_greenhouse() + fetch_lever() + fetch_ashby()
    seen, out = set(), []
    for j in raw:
        fp = _norm(j["company"] + j["title"])
        if fp in seen:
            continue
        seen.add(fp)
        out.append(j)
    return out
