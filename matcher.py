"""Job Hunter - Matcher.

Pipeline de scoring para ofertas de trabajo remoto. Modular y limpio.

Etapas:
1. Normalizar la oferta (title, text, salary).
2. Aplicar filtros duros (idioma, ubicación, modalidad, scam).
3. Calcular score con reglas declarativas.
4. Asignar banda (APPLY / REVIEW / IGNORE).
"""

import re
from collections import Counter

# ============================================================================
# 1. STOPWORDS / IDIOMAS
# ============================================================================

STOPWORDS = set("""
a an and are as at be by for from has have how i in is it its of on or that the this to
was were will with you your we our they their she he his her job jobs work works role
position company team teams experience years year working knowledge ability skills skill
required requirements responsibilities including within across using used use good strong
excellent ability communicate communication english spanish candidate ideal perfect great
join joining looking want need apply application applicants posted today weekly full time
part fulltime parttime salary plus benefits like make made day days month months week weeks
hour hours min etc description about who what where why when which while through into
around beyond any all both each few more most other some such only own same than too very
can just should now also even many much one two first new old high higher low strong key
main per via based located location anywhere world worldwide global international office
headquarters hq homebase business customers customer support services service solutions
""".split())

WORD_RE = re.compile(r"[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ]{3,}")


def tokenize(text):
    """Tokeniza un texto, quita stopwords, devuelve lista en minúsculas."""
    return [w for w in WORD_RE.findall((text or "").lower()) if w not in STOPWORDS]


def hot_keywords(jobs, top=40):
    counter = Counter()
    for j in jobs:
        counter.update(tokenize(" ".join([
            j.get("title") or "",
            " ".join(j.get("tags") or []),
            (j.get("description") or "")[:1200],
        ])))
    return [w for w, _ in counter.most_common(top)]


def build_keywords(profile):
    """Keywords de búsqueda = skills del perfil + extras + headline."""
    kw = set()
    for group in profile.get("skills", {}).values():
        for s in group:
            s = (s or "").strip()
            if s:
                kw.add(s.lower())
    for s in profile.get("extra_keywords", []):
        s = (s or "").strip()
        if s:
            kw.add(s.lower())
    for w in tokenize(profile.get("headline", "")):
        if len(w) > 2:
            kw.add(w)
    return sorted(kw)


# ============================================================================
# 2. LÉXICO DE ROLES (categorías de ofertas)
# ============================================================================

# Roles entry-level que el candidato PUEDE defender.
INCLUDE_ROLES = {
    "support", "help desk", "helpdesk", "customer service", "customer care",
    "customer success", "client support", "client services", "user support",
    "technical support", "tech support", "live chat", "chat support",
    "community manager", "community moderator", "community operations",
    "moderator", "moderation", "ambassador", "discord", "telegram",
    "operations", "ops", "coordinator", "operations associate",
    "research", "analyst", "intelligence", "due diligence",
    "trader", "trading", "trading assistant",
    "kyc", "aml", "compliance", "risk", "fraud", "onboarding", "trust",
    "content", "writer", "copywriter", "editor", "documentation",
    "assistant", "associate", "virtual assistant",
    "listings", "curation", "reviewer", "evaluator", "annotator", "labeler",
    "data entry", "admin", "back office",
    "voice", "narration", "audio", "transcription", "transcriber",
    "qa", "quality assurance", "tester", "ai trainer", "ai tutor",
    "data annotator", "prompt", "rater", "evaluator",
    "social media", "growth", "implementation", "specialist",
    "payment operations", "support operations", "customer operations",
    "inbound sales", "account executive", "business development",
    "client onboarding", "user onboarding", "implementation specialist",
    "product support", "help center", "ticketing",
}

# Palabras que, combinadas con otras, indican un rol INADECUADO.
EXCLUDE_TITLE_TOKENS = {
    "senior", "lead", "principal", "head of", "director", "chief", "vp ",
    "vice president", "manager",  # sin junior al lado
    "engineer", "developer", "programmer", "scientist", "architect",
    "outbound", "cold call", "appointment setter", "telemarketing",
}

# Junior/entry: anula el exclude.
JUNIOR_TOKENS = {"junior", "entry", "entry-level", "graduate", "trainee", "intern"}

# Títulos que el candidato NO puede defender (ignoran ofertas, sin importar keywords).
TECH_TITLE_BLOCK = re.compile(
    r"\b(engineer|developer|programmer|scientist|architect|devops|sre|"
    r"development\s+(talent|engineer|manager|lead|architect))\b", re.I)

# Idiomas que el candidato NO habla.
UNSUPPORTED_LANGUAGES = {"german", "french", "italian", "portuguese"}


# ============================================================================
# 3. FILTROS DUROS
# ============================================================================

# Roles creativos / edición profesional: no defendibles.
CREATIVE_TITLE = re.compile(
    r"\b(video\s*editor|video\s*editing|motion\s*designer|motion\s*graphics|"
    r"ux\s*designer|ui\s*designer|product\s*designer|brand\s*designer|"
    r"illustrator|3d\s*artist|3d\s*designer|sound\s*designer|audio\s*engineer|"
    r"video\s*producer|video\s*production|video\s*post[- ]production|"
    r"graphic\s*designer|graphic\s*design|"
    r"photo\s*editor|photo\s*retoucher|"
    r"character\s*(concept\s*)?artist|concept\s*artist|"
    r"2d\s*artist|3d\s*modeler|3d\s*animator|"
    r"web\s*designer|designer|"
    r"interior\s*designer|revit|"
    r"fashion\s*designer|"
    r"music\s*producer|music\s*composer|"
    r"\bcad\b|cad\s*designer|cad\s*modeler)\b", re.I)

# Modalidad phone-heavy: bajar a REVIEW.
PHONE_HEAVY_RE = re.compile(
    r"\b(phone\s*support|phone\s*customer|phone\s*based|call\s*center|"
    r"call\s*centre|inbound\s*calls|outbound\s*calls|voice\s*support|"
    r"voice\s*chat\s*support|high\s*volume\s*calls|customer\s*phone|"
    r"telephony|answer(ing)?\s*(incoming|outgoing)\s*calls|"
    r"handle\s*(incoming|outgoing)\s*calls|"
    r"make\s*(outgoing|outbound)\s*calls|"
    r"cold\s*call|talk\s*to\s*customers?\s*over\s*the\s*phone|"
    r"provide\s*phone\s*support|appointment\s*setter|"
    r"appointment\s*setting|outbound\s*(sales|caller|agent|rep)|"
    r"telemarket(er|ing)|door[- ]to[- ]door|"
    r"dial(er|ing)\s*(for|to)|business\s*development\s*outbound|"
    r"\bbdr\s*outbound|\bsdr\s*outbound|"
    r"lead\s*generation\s*(outbound|cold)|outbound\s*prospecting|"
    r"high\s*volume\s*outbound)\b", re.I)

# Modalidad async / chat / email: NO penalizar.
ASYNC_SUPPORT_RE = re.compile(
    r"\b(chat\s*support|live\s*chat|email\s*support|"
    r"slack|discord|telegram|intercom|zendesk|freshdesk|"
    r"help\s*center|knowledge\s*base|ticketing|ticket\s*system|"
    r"help\s*desk|helpdesk|asynchronous|async|"
    r"text\s*based|written\s*support|non[- ]?voice|chat[- ]?first)\b", re.I)

# Años de experiencia requeridos: si pide 3+ años y NO es junior -> IGNORE.
YEARS_REQUIRED_RE = re.compile(
    r"\b([3-9]\+?\s*years?|[1-9]\d\+?\s*years?|"
    r"3[-–][5-9]\s*years?|4[-–][6-9]\s*years?|5[-–][7-9]\s*years?|"
    r"minimum\s+[3-9]\s*years?|at\s+least\s+[3-9]\s*years?|"
    r"extensive\s+(experience|background|track\s*record)|"
    r"proven\s*track\s*record|seasoned\s+(professional|candidate|trader))\b",
    re.I)

# Senioridad alta sin marca junior -> IGNORE.
SENIOR_TITLE_RE = re.compile(
    r"\b(senior|lead|principal|director|head\s+of|chief|vice\s*president|\bvp\b)\b", re.I)

# Ubicación: solo remoto global / LATAM / Paraguay-friendly.
COUNTRY_BLOCKED_RE = re.compile(
    r"\b(united\s+states|\busa\b|u\.?s\.?a?\.?|united\s+kingdom|\buk\b|"
    r"germany|france|spain|italy|netherlands|poland|portugal|"
    r"greece|cyprus|czech|canada|philippines|singapore|australia|"
    r"taiwan|pakistan|india|japan|sweden|norway|denmark|finland|"
    r"ireland|switzerland|austria|belgium|china|south\s+korea|"
    r"malaysia|indonesia|thailand|vietnam|turkey|israel|dubai|uae|"
    r"saudi|qatar|europe|emea|asia)\b", re.I)

LOCATION_SAFE_RE = re.compile(
    r"\b(worldwide|global|globally|anywhere|around\s+the\s+world|"
    r"latin\s+america|\blatam\b|south\s+america|central\s+america|"
    r"americas|ecuador|bolivia|venezuela|panama|guatemala|"
    r"honduras|nicaragua|el\s+salvador|costa\s+rica|"
    r"dominican\s+republic|puerto\s+rico|cuba|paraguay)\b", re.I)

# Presencia física obligatoria.
IN_PERSON_RE = re.compile(
    r"\b(onboard(ing)?\s+(in\s+person|on[- ]site|at\s+our\s+office)|"
    r"in[- ]person\s+onboarding|on[- ]site\s+onboarding|"
    r"must\s+(attend|complete|do)\s+onboarding|"
    r"onboarding\s+(is|will\s+be)\s+(in\s+person|on[- ]site)|"
    r"physical\s+office|our\s+offices\s+(in|are)|"
    r"relocat\w*\s+required|must\s+relocat\w*|"
    r"work\s+from\s+(the\s+)?office|"
    r"office\s+(attendance|presence|presencial)|"
    r"in[- ]office\s+(requirement|days|attendance)|"
    r"come\s+into\s+the\s+office)\b", re.I)

# Híbrido.
HYBRID_RE = re.compile(
    r"\bhybrid\b|on[- ]site\s+(days|requirement)|"
    r"in[- ]office\s+(days|requirement)|office[- ]based|"
    r"presencial\s+(days|requirement)|"
    r"work\s+from\s+office\s+(days|some)", re.I)

# Pago por hora o por proyecto.
PER_PROJECT_RE = re.compile(
    r"\b(per\s+project|project[- ]based|per\s+gig|one[- ]time|"
    r"per\s+task|piece\s+work|100%\s*commission|commission[- ]only|"
    r"pay[- ]per|per\s+assignment|short[- ]term\s+gig)\b", re.I)

HOURLY_RE = re.compile(r"\b(per\s+hour|hourly|per\s+hr|/hr\b|by\s+the\s+hour)\b", re.I)

# Empresa explícitamente bloqueada.
COMPANY_BLOCKLIST = {"stripe", "mercury", "joby", "zapiet"}
COMPANY_BLOCKLIST_RE = re.compile(
    r"\b(" + "|".join(re.escape(c) for c in COMPANY_BLOCKLIST) + r")\b", re.I)

# Remote world.
REMOTE_RE = re.compile(
    r"\b(remote|worldwide|global|anywhere|distributed|work\s+from\s+home|"
    r"wfh|100%\s*home|work[- ]at[- ]home)\b", re.I)


# ============================================================================
# 4. FILTRO DE IDIOMA
# ============================================================================

GERMAN_MARKERS = {"und", "der", "die", "das", "wir", "sie", "ihnen", "ihre",
                  "kunden", "aufgaben", "anforderungen", "kenntnisse",
                  "erfahrung", "stelle", "unternehmen", "außerdem", "möchten"}
FRENCH_MARKERS = {"les", "des", "une", "nous", "vous", "être", "avoir",
                  "poste", "entreprise", "expérience", "candidature",
                  "salaire", "compétences", "désirons", "également"}
ITALIAN_MARKERS = {"della", "delle", "questo", "questa", "essere", "avere",
                   "lavoro", "azienda", "italiano", "inglese", "stage",
                   "competenze", "ricerchiamo"}
PORTUGUESE_MARKERS = {"não", "são", "está", "também", "ainda", "muito",
                      "trabalho", "empresa", "experiência", "salário",
                      "vaga", "equipe", "competências", "procuramos"}
SPANISH_MARKERS = {"el", "la", "los", "las", "de", "del", "para", "con",
                   "por", "que", "como", "trabajo", "empresa", "experiencia",
                   "requisitos", "salario", "años", "habilidades", "equipo",
                   "remoto", "puesto", "candidato", "aplicar"}

LANG_MARKERS = {
    "spanish": SPANISH_MARKERS,
    "german": GERMAN_MARKERS,
    "french": FRENCH_MARKERS,
    "italian": ITALIAN_MARKERS,
    "portuguese": PORTUGUESE_MARKERS,
}


def detect_language(desc):
    """Detecta idioma principal. Devuelve string ('spanish', 'english', 'german', ...)."""
    low = (desc or "").lower()
    words = re.findall(r"[a-z]{2,}", low)
    if not words:
        return "english"
    counts = {lang: sum(1 for w in words if w in markers)
              for lang, markers in LANG_MARKERS.items()}
    sorted_langs = sorted(counts.items(), key=lambda x: -x[1])
    lang, score = sorted_langs[0]
    second = sorted_langs[1][1]
    if (score >= 8
        and score / len(words) >= 0.03
        and score >= second * 2
        and lang in UNSUPPORTED_LANGUAGES):
        return lang
    return "english"


# ============================================================================
# 5. SALARIO
# ============================================================================

def parse_salary(text):
    """Convierte texto de salario a USD/mes. Devuelve dict o None."""
    if not text or not str(text).strip():
        return None
    t = str(text).lower()
    per_hour = bool(re.search(r"per\s*hour|/h\b|hourly|\bhr\b", t))
    per_year = bool(re.search(r"per\s*(year|annum)|/y\b|/yr\b|annual|yearly", t))
    vals = []
    for n in re.findall(r"\d[\d.,]*", t):
        n2 = n.replace(",", "")
        if "." in n2:
            a, b = n2.split(".", 1)
            n2 = a + b if len(b) == 3 else a + "." + b[:2]
        try:
            vals.append(float(n2))
        except ValueError:
            pass
    if not vals:
        return None
    lo, hi = min(vals), max(vals)
    if per_hour:
        lo, hi = lo * 160, hi * 160
    elif per_year or lo > 20000:
        lo, hi = lo / 12, hi / 12
    return {"min": round(lo), "max": round(hi), "raw": str(text)[:70]}


def salary_marker(parsed, floor=1000, target=1300):
    """🔴 por debajo · 🟡 aceptable · 🟢 cumple objetivo · ⚪ sin dato."""
    if not parsed:
        return {"marker": "⚪", "label": "sin salario publicado", "ok": None}
    lo = parsed["min"]
    if lo >= target:
        return {"marker": "🟢", "label": f"cumple objetivo (${lo:,}/mes)", "ok": True}
    if lo >= floor:
        return {"marker": "🟡", "label": f"aceptable (${lo:,}/mes)", "ok": True}
    return {"marker": "🔴", "label": f"bajo mínimo (${lo:,}/mes)", "ok": False}


# ============================================================================
# 6. KEYWORDS DE SCORING
# ============================================================================

CRYPTO_KW = ["crypto", "cryptocurrency", "bitcoin", "btc", "ethereum", "eth",
             "cardano", "solana", "blockchain", "web3", "defi", "nft",
             "wallet", "wallets", "ledger", "metamask", "phantom",
             "staking", "tokenomics", "airdrop", "kyc", "liquidity",
             "binance", "kraken", "kucoin", "bybit", "okx", "coinbase",
             "smart contract", "stablecoin", "blockchain.com"]

AI_KW = ["ai trainer", "ai tutor", "ai rater", "ai ", "artificial intelligence",
         "machine learning", " llm", "gpt", "chatgpt", "claude",
         "prompt engineer", "generative ai", "data annotat",
         "training data", "neural network", "data label"]

FINTECH_KW = ["fintech", "payment", "remittance", "banking", "swift",
              "aml", "fraud", "chargeback", "reconciliation", "compliance"]

CUSTOMER_KW = ["customer support", "customer service", "customer care",
               "customer success", "client support", "client services",
               "user support", "technical support", "tech support",
               "help desk", "helpdesk", "live chat", "chat support",
               "zendesk", "intercom", "freshdesk", "ticketing"]

OPS_KW = ["operations", " ops ", "coordinator", "workflow",
          "process", "onboarding", "offboarding", "back office"]

COMMUNITY_KW = ["community manager", "community moderator", "discord",
                "telegram", "moderation", "moderator", "ambassador",
                "engagement", "evangelist", "user education"]

TRADING_KW = ["trader", "trading", "trade", "market analysis",
              "technical analysis", "chart", "indicator", "rsi", "macd",
              "support", "resistance", "trend", "pattern", "volume",
              "market order", "limit order", "stop loss", "take profit",
              "leverage", "long", "short", "spot", "perp", "perpetual",
              "futures", "options", "order book", "liquidity", "spread",
              "position size", "position sizing", "risk management",
              "price action", "tradingview", "bybit", "okx", "binance"]

BILINGUAL_KW = ["spanish", "español", "espanol", "bilingual", "bilingual ",
                "english and spanish", "english / spanish", "english/spanish",
                "spanish and english", "spanish / english", "spanish/english"]


def _kw_hits(text, kws):
    """Cuenta cuántas keywords (case-insensitive, word-boundary) aparecen en text."""
    text = (text or "").lower()
    n = 0
    for k in kws:
        k_low = k.lower().strip()
        if not k_low:
            continue
        if re.search(r"(?<![a-z0-9])" + re.escape(k_low) + r"(?![a-z0-9])", text):
            n += 1
    return n


# ============================================================================
# 7. PIPELINE PRINCIPAL
# ============================================================================

def _flatten_tags(raw):
    """Aplana tags (puede contener dicts o listas anidadas) a lista de str."""
    out = []
    for t in (raw or []):
        if isinstance(t, str):
            out.append(t)
        elif isinstance(t, dict):
            out.append(str(t.get("name", "")))
        elif isinstance(t, list):
            for sub in t:
                if isinstance(sub, str):
                    out.append(sub)
                elif isinstance(sub, dict):
                    out.append(str(sub.get("name", "")))
    return out


def hard_filters(job):
    """Aplica filtros duros. Devuelve (cap_max, forced_band) o ('IGNORE', 'IGNORE')."""
    title = (job.get("title") or "").lower()
    desc = (job.get("description") or "")
    if not isinstance(desc, str):
        desc = ""
    flat_tags = _flatten_tags(job.get("tags"))
    text = (title + " " + " ".join(flat_tags) + " " + desc[:7000]).lower()
    loc = (job.get("location") or "")
    company = (job.get("company") or "")

    if CREATIVE_TITLE.search(title):
        return 0, "IGNORE"
    if TECH_TITLE_BLOCK.search(title):
        return 0, "IGNORE"
    if detect_language(desc) in UNSUPPORTED_LANGUAGES:
        return 0, "IGNORE"

    first_para = desc[:1200]
    if (YEARS_REQUIRED_RE.search(title) or YEARS_REQUIRED_RE.search(first_para)):
        if not re.search(r"\b(junior|entry|graduate|trainee|intern)\b", title, re.I):
            return 0, "IGNORE"

    company_blob = f"{company} {title} {text[:500]}"
    if COMPANY_BLOCKLIST_RE.search(company_blob):
        return 0, "IGNORE"

    if SENIOR_TITLE_RE.search(title) and not re.search(
        r"\b(junior|entry|graduate|trainee|intern)\b", title, re.I):
        return 0, "IGNORE"

    if re.search(r"\bmanager\b", title, re.I):
        return 0, "IGNORE"

    if IN_PERSON_RE.search(text):
        return 0, "IGNORE"

    if HYBRID_RE.search(text):
        return 0, "IGNORE"

    if _location_restricted(loc, text, title):
        return 0, "IGNORE"

    cap = 100
    if PHONE_HEAVY_RE.search(title) or PHONE_HEAVY_RE.search(text[:3000]):
        if not ASYNC_SUPPORT_RE.search(text[:3000]):
            cap = min(cap, 65)
    if PER_PROJECT_RE.search(text):
        cap = min(cap, 65)
    if HOURLY_RE.search(text):
        cap = min(cap, 75)

    return cap, None


def _location_restricted(loc, text, title):
    """True si la oferta NO se puede tomar desde Paraguay/remoto global."""
    title_norm = _loc_norm(title)
    loc_norm = _loc_norm(loc)

    if COUNTRY_BLOCKED_RE.search(title_norm) and not LOCATION_SAFE_RE.search(title_norm):
        return True
    if COUNTRY_BLOCKED_RE.search(loc_norm) and not LOCATION_SAFE_RE.search(loc_norm):
        return True
    if re.search(r"\b(must|required|need\s+to)\s+be\s+(based|located|live)\s+in\b",
                 text, re.I):
        return True
    return False


_NO_TILDES = str.maketrans({
    "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n",
    "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U", "Ñ": "N",
})


def _loc_norm(s):
    return (s or "").translate(_NO_TILDES)


# ============================================================================
# 8. SCORING
# ============================================================================

def _domain_score(title, text):
    """Solo se usa para ordenar prioridad, no para filtrar."""
    title_crypto = _kw_hits(title, CRYPTO_KW) + _kw_hits(title, AI_KW) + _kw_hits(title, FINTECH_KW)
    if title_crypto >= 1:
        return 1.0
    return 0.85


def _category_score(title, text):
    """Puntúa según categorías de rol encontradas en el TÍTULO."""
    title_cats = [
        _kw_hits(title, CUSTOMER_KW),
        _kw_hits(title, OPS_KW),
        _kw_hits(title, COMMUNITY_KW),
        _kw_hits(title, TRADING_KW),
        _kw_hits(title, AI_KW),
        _kw_hits(title, CRYPTO_KW),
    ]
    title_max = max(title_cats) if title_cats else 0
    if title_max >= 1:
        return min(1.0, 0.6 + 0.4 * min(title_max, 3) / 3)
    return 0.2


def _bilingual_bonus(text):
    return 1.0 if _kw_hits(text, BILINGUAL_KW) > 0 else 0.0


def _remote_score(job, text):
    loc = (job.get("location") or "").lower()
    if "remote" in loc or REMOTE_RE.search(text[:600]):
        return 1.0
    return 0.3


def _salary_score(parsed, floor, target):
    if not parsed:
        return 0.5
    lo = parsed["min"]
    if lo >= target:
        return 1.0
    if lo >= floor:
        return 0.7
    return 0.3


def _seniority_score(title):
    if re.search(r"\b(junior|entry|graduate|trainee|intern)\b", title, re.I):
        return 1.0
    if re.search(r"\b(senior|lead|principal|head|director|chief)\b", title, re.I):
        return 0.3
    return 0.7


def _english_score(text):
    if detect_language(text) == "spanish":
        return 0.85
    return 1.0


WEIGHTS = {
    "domain": 20,
    "category": 25,
    "bilingual": 5,
    "remote": 15,
    "salary": 15,
    "seniority": 10,
    "english": 10,
}


def score_offer(job, profile):
    """Puntúa una oferta. Devuelve dict con score, band, emoji, etc."""
    salary_cfg = profile.get("salary", {})
    floor = salary_cfg.get("floor", 1000)
    target = salary_cfg.get("target_min", 1300)

    title = (job.get("title") or "")
    title_low = title.lower()
    desc = (job.get("description") or "")
    flat_tags = _flatten_tags(job.get("tags"))
    text = (title_low + " " + " ".join(flat_tags) + " " + (desc if isinstance(desc, str) else "")[:7000]).lower()

    cap, forced = hard_filters(job)
    if forced == "IGNORE":
        return {
            "score": 0,
            "band": "IGNORE",
            "emoji": "⚪",
            "track": None,
            "salary_parsed": None,
            "salary_marker": {"marker": "⚪", "label": "filtrada", "ok": None},
            "components": {},
            "reasons": ["filtrada por reglas duras"],
        }

    parsed = parse_salary(job.get("salary") or "")
    components = {
        "domain": _domain_score(title_low, text),
        "category": _category_score(title_low, text),
        "bilingual": _bilingual_bonus(text),
        "remote": _remote_score(job, text),
        "salary": _salary_score(parsed, floor, target),
        "seniority": _seniority_score(title_low),
        "english": _english_score(desc),
    }

    raw = sum(WEIGHTS[k] * c for k, c in components.items())
    score = round(raw)
    score = min(score, cap)

    if parsed and parsed["min"] < floor:
        score = min(score, 65)

    if score >= 90:
        band, emoji = "APPLY NOW", "🔥"
    elif score >= 75:
        band, emoji = "APPLY", "🟢"
    elif score >= 60:
        band, emoji = "REVIEW", "🟡"
    else:
        band, emoji = "IGNORE", "⚪"

    reasons = []
    if components["category"] >= 0.75:
        reasons.append("rol entry defendible")
    if components["domain"] >= 0.95:
        reasons.append("dominio crypto/AI/fintech")
    if components["bilingual"] >= 1.0:
        reasons.append("bilingüe ✓")
    if components["remote"] >= 1.0:
        reasons.append("remoto ✓")
    if parsed and parsed["min"] >= target:
        reasons.append("salario al objetivo")
    elif parsed:
        marker = salary_marker(parsed, floor, target)
        reasons.append(f"salario {marker['marker']}")
    if components["seniority"] >= 1.0:
        reasons.append("junior/entry ✓")
    elif components["seniority"] <= 0.4:
        reasons.append("senior (no ideal)")

    return {
        "score": score,
        "band": band,
        "emoji": emoji,
        "track": _track_from_components(components),
        "salary_parsed": parsed,
        "salary_marker": salary_marker(parsed, floor, target),
        "components": components,
        "reasons": reasons,
    }


def _track_from_components(components):
    if components.get("domain", 0) >= 0.95:
        return "crypto/AI/fintech"
    return "general"


# ============================================================================
# 9. COMPATIBILIDAD
# ============================================================================

def family_match(job, profile):
    """Devuelve keywords del perfil que aparecen en la oferta (max 14)."""
    text = " ".join([
        job.get("title", ""),
        " ".join(job.get("tags") or []),
        (job.get("description") or "")[:3000],
    ]).lower()
    kws = set()
    for group in profile.get("skills", {}).values():
        for s in group:
            s = s.strip().lower()
            if s and re.search(r"(?<![a-z0-9])" + re.escape(s) + r"(?![a-z0-9])", text):
                kws.add(s)
    for s in profile.get("extra_keywords", []):
        s = s.strip().lower()
        if s and re.search(r"(?<![a-z0-9])" + re.escape(s) + r"(?![a-z0-9])", text):
            kws.add(s)
    return sorted(kws)[:14]
