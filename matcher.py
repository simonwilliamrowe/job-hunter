"""
Job Hunter — Motor de inteligencia de ofertas v2.

Scoring ponderado por CARRIL (track): cada oferta recibe una puntuación
0-100 por cada familia de puesto con pesos específicos, bandas de decisión
(APPLY NOW / APPLY / REVIEW / IGNORE), desglose de motivos, parser salarial
con marcadores 🔴🟡🟢 y persona de CV recomendada.
"""
import re
from collections import Counter

# ---------------------------------------------------------------------------
# léxico por criterio
# ---------------------------------------------------------------------------

CRYPTO_KW = ["crypto", "cryptocurrency", "bitcoin", "btc", "ethereum", "eth", "cardano",
             "solana", "blockchain", "web3", "defi", "dex", "cex", "exchange", "wallet",
             "wallets", "ledger", "metamask", "phantom", "staking", "token", "tokens",
             "tokenomics", "nft", "nfts", "dao", "daos", "airdrop", "custody", "seed phrase",
             "private key", "public key", "gas fee", "transaction", "transactions",
             "on-chain", "onchain", "kyc", "liquidity", "market cap", "trading", "binance",
             "kraken", "kucoin", "bitget", "coinbase", "decentralized", "smart contract",
             "layer 2", "bridge", "yield", "protocol", "tokenized", "stablecoin"]

SUPPORT_KW = ["support", "customer service", "helpdesk", "help desk", "ticket", "tickets",
              "zendesk", "intercom", "freshdesk", "live chat", "chat support", "email support",
              "customer success", "account manager", "escalation", "sla", "csat",
              "customer experience", "client support", "user support", "onboarding",
              "troubleshoot", "troubleshooting", "faq", "knowledge base", "resolution",
              "satisfaction", "queries", "inquiries", "agents", "support specialist"]

COMMUNITY_KW = ["community", "moderation", "moderator", "discord", "telegram", "ambassador",
                "engagement", "evangelist", "social", "forum", "forums", "reddit",
                "user education", "educational content", "events", "meetup", "influencer",
                "community manager", "community support", "content creation", "shorts"]

RESEARCH_KW = ["research", "analyst", "analysis", "tokenomics", "due diligence", "diligence",
               "fundamental", "market research", "competitive", "intelligence", "whitepaper",
               "white paper", "data analysis", "report", "reports", "writeups", "coverage",
               "dashboard", "metrics", "nansen", "dune", "glassnode", "on-chain analysis",
               "research assistant", "researcher"]

# Trading junior/entry-level: detecta ofertas tipo "Junior Crypto Trader",
# "Entry Level Trader", "Trading Analyst (Junior)" etc. Cubre conceptos
# técnicos (TA, indicators, order types, leverage, risk management) y
# el lado de mercados (market, limit, spot, perp, futures, charts).
TRADING_KW = ["trader", "trading", "trade", "trades", "market analysis", "technical analysis",
              "chart", "charts", "charting", "candlestick", "candlesticks", "indicator",
              "indicators", "rsi", "macd", "moving average", "moving averages", "fibonacci",
              "support", "resistance", "trend", "trends", "breakout", "pattern", "patterns",
              "volume", "market order", "market orders", "limit order", "limit orders",
              "stop loss", "take profit", "leverage", "long", "short", "long position",
              "short position", "spot", "perp", "perpetual", "perpetuals", "futures",
              "options", "derivative", "derivatives", "order book", "orderbook",
              "liquidity", "slippage", "spread", "spreads", "position size", "position sizing",
              "risk management", "risk reward", "stop loss", "trailing stop", "swing trade",
              "day trade", "day trading", "swing trading", "scalping", "scalp", "scalper",
              "trade journal", "trading journal", "backtest", "backtesting", "strategy",
              "strategies", "trading strategy", "trading strategies", "trade setup",
              "price action", "market structure", "tradingview", "trading view", "binance",
              "bybit", "okx", "bitfinex", "bitmex", "deribit", "order execution",
              "exchange", "exchanges", "market maker", "market making", "trading desk",
              "trading floor", "proprietary", "prop trading", "prop firm", "alpha",
              "beta", "volatility", "vol", "open interest", "funding rate", "funding rates",
              "liquidation", "liquidations"]

FINTECH_KW = ["fintech", "payment", "payments", "banking", "bank", "remittance", "sepa",
              "swift", "aml", "fraud", "chargeback", "reconciliation", "accounting", "risk",
              "compliance", "money transfer", "merchant", "financial", "finance", "kym",
              "kyc", "transfer", "transfers", "wires"]

OPS_KW = ["operations", "ops", "process", "workflow", "workflows", "coordination",
          "logistics", "scheduling", "reporting", "data entry", "automation", "admin",
          "administrative", "vendor", "inventory", "quality assurance", "onboarding",
          "offboarding", "operations associate", "operational"]

TOOLS_KW = ["zendesk", "intercom", "freshdesk", "gorgias", "slack", "discord", "telegram",
            "notion", "jira", "asana", "trello", "hubspot", "salesforce", "excel", "sheets",
            "google workspace", "crm", "crisp", "front", "kustomer", "help scout", "helpscout",
            "ticketing"]

JUNIOR_KW = ["junior", "entry", "entry-level", "graduate", "trainee", "intern", "associate",
             "2+ years", "1+ years", "0-2 years", "0-3 years", "no experience"]

SENIOR_KW = ["senior", "lead", "head of", "principal", "staff", "director", "manager",
             "5+ years", "7+ years", "10+ years", "expert"]

ENGLISH_WORDS = set("""the and you your we our will are with this that for have has not but
they from team work role position apply experience skills about what who when where please
would could should also can more other such only their there these those than then them out
over under into after before between just because each which while during within without
through across among both few many most some any all own same too very just should now even
""".split())

EN_RE = re.compile(r"[a-z]{2,}")
SPANISH_RE = re.compile(r"\b(spanish|español|biling[uo]e|bilingual)\b", re.I)
def _kw_rx(k):
    return re.compile(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])")


def _kw_count(text, kws, title_text="", title_weight=3.0, cap=10.0):
    cnt = 0.0
    for k in kws:
        rx = _kw_rx(k)
        if re.search(rx, title_text):
            cnt += title_weight
        elif re.search(rx, text):
            cnt += 1.0
    return min(1.0, cnt / cap)


SPANISH_MARKERS = {
    "el", "la", "los", "las", "de", "del", "para", "con", "por", "que", "como",
    "trabajo", "trabajar", "empresa", "experiencia", "requisitos", "salario",
    "años", "habilidades", "equipo", "remoto", "puesto", "candidato", "aplicar",
    "vacante", "nuestra", "nuestro", "ser", "estar", "tener", "hacer", "más",
    "menos", "entre", "sobre", "durante", "después", "antes", "también", "muy",
    "bueno", "buena", "gran", "grande", "persona", "personas", "idioma",
}

# Marcadores de idiomas que el candidato NO habla.
# El bot debe BLOQUEAR ofertas en estos idiomas (no aplicar).
GERMAN_MARKERS = {
    # palabras alemanas comunes en ofertas
    "und", "der", "die", "das", "wir", "sie", "mit", "von", "für", "ist",
    "sind", "auf", "bei", "nicht", "auch", "kunden", "kunde", "aufgaben",
    "erfahrung", "kenntnisse", "bewerbung", "stelle", "stellenangebot",
    "mitarbeiter", "unternehmen", "arbeit", "beruf", "tätigkeiten", "anforderungen",
    "homeoffice", "deutsch", "englisch", "sprachkenntnisse", "muttersprache",
    "team", "abteilung", "bereich", "kenntnisse", "quereinsteiger",
    "bewerben", "vollzeit", "teilzeit", "festanstellung", "praktikum",
    "ausbildung", "studium", "berufserfahrung", "wechsel", "möglichkeit",
    "gerne", "freuen", "kennenzulernen", "interessiert", "anfragen", "ihre",
    "ihnen", "unsere", "unser", "einem", "einer", "eines", "werden", "sollten",
    "können", "müssen", "dürfen", "wollen", "möchten", "gerne", "bitte",
    "vielen", "dank", "kontakt", "anschrift", "telefon", "bewerbungsschreiben",
    "lebenslauf", "zeugnisse", "qualifikation", "weiterbildung", "gehalt",
    "verhandlung", "leistungen", "anstellung", "vertrag", "woche", "monat",
    "jahr", "stunde", "stunden", "täglich", "wochentags", "pendeln",
}

FRENCH_MARKERS = {
    "et", "le", "la", "les", "des", "un", "une", "avec", "pour", "par",
    "nous", "vous", "ils", "elles", "est", "sont", "être", "avoir",
    "expérience", "poste", "entreprise", "candidature", "salaire", "cdi", "cdd",
    "français", "anglais", "équipe", "département", "télétravail", "embauche",
    "intérim", "stage", "alternance", "compétences", "qualification",
    "responsabilités", "profil", "recherchons", "cherchons", "souhaitons",
    "désirons", "postuler", "embaucher", "rémunération", "avantages",
    "mutuelle", "transport", "tickets", "restaurant", "cadre", "employé",
}

ITALIAN_MARKERS = {
    "e", "il", "la", "di", "del", "della", "con", "per", "da", "in", "su",
    "noi", "voi", "loro", "essere", "avere", "lavoro", "lavorare",
    "esperienza", "azienda", "stipendio", "retribuzione", "collaborazione",
    "italiano", "inglese", "squadra", "dipartimento", "smartworking",
    "remoto", "presenza", "ufficio", "cliente", "clienti", "fornitore",
    "fornitori", "contratto", "tempo", "indeterminato", "determinato",
    "stage", "tirocinio", "apprendistato", "competenze", "qualifiche",
    "responsabilità", "mansioni", "ricerchiamo", "cerchiamo", "desideriamo",
    "candidatura", "inviare", "colloquio", "conoscenza", "madrelingua",
}

PORTUGUESE_MARKERS = {
    "e", "o", "a", "os", "as", "de", "do", "da", "dos", "das", "com", "por",
    "para", "em", "no", "na", "nos", "nas", "se", "que", "não", "são",
    "trabalho", "trabalhar", "empresa", "experiência", "salário", "cargo",
    "vaga", "candidatura", "equipe", "departamento", "remoto", "presencial",
    "escritório", "cliente", "clientes", "fornecedor", "contrato",
    "indeterminado", "determinado", "estágio", "trainee", "jovem",
    "aprendiz", "competências", "habilidades", "requisitos", "responsabilidades",
    "procuramos", "buscamos", "desejável", "desejamos", "enviar", "conhecimento",
    "português", "inglês", "espanhol", "língua", "fluente", "nativo",
}


def detect_language(desc):
    """Detecta el idioma del anuncio. Devuelve uno de:
    'spanish', 'english', 'german', 'french', 'italian', 'portuguese', 'unknown'.

    Estrategia: contar marcadores de cada idioma. Si hay señales claras de
    un idioma no soportado, devolverlo (para que el caller pueda bloquear).
    Si no hay señales claras de NINGÚN idioma, devolver 'english' (asumimos
    que los anuncios remotos globales están en inglés por default)."""
    low = (desc or "").lower()
    words = EN_RE.findall(low)
    if not words:
        return "english"  # sin palabras reconocibles -> asumimos inglés
    counts = {
        "spanish": sum(1 for w in words if w in SPANISH_MARKERS),
        "german": sum(1 for w in words if w in GERMAN_MARKERS),
        "french": sum(1 for w in words if w in FRENCH_MARKERS),
        "italian": sum(1 for w in words if w in ITALIAN_MARKERS),
        "portuguese": sum(1 for w in words if w in PORTUGUESE_MARKERS),
    }
    # Idioma ganador: el de mayor count, pero solo si tiene señales claras
    lang, score = max(counts.items(), key=lambda x: x[1])
    if score >= 5:  # al menos 5 marcadores -> señal clara
        return lang
    return "english"  # sin señales claras -> asumimos inglés


def is_english(desc):
    """DEPRECATED: usar detect_language() en su lugar.
    Devuelve True si el anuncio está en inglés (o en un idioma no detectado).
    Devuelve False solo si es español (que sí soportamos)."""
    lang = detect_language(desc)
    return lang != "spanish"


# Lista de idiomas NO soportados por el candidato.
# Si una oferta está en uno de estos idiomas, debe ser IGNOREada.
UNSUPPORTED_LANGUAGES = {"german", "french", "italian", "portuguese"}


def is_unsupported_language(desc):
    """True si el anuncio está en un idioma que el candidato NO habla
    (alemán, francés, italiano, portugués)."""
    return detect_language(desc) in UNSUPPORTED_LANGUAGES


def parse_salary(raw):
    """Convierte cualquier texto de salario a USD/mes. Devuelve dict o None."""
    if not raw or not str(raw).strip():
        return None
    t = str(raw).lower()
    per_hour = bool(re.search(r"per\s*hour|/h\b|hourly|\bhr\b", t))
    per_month = bool(re.search(r"per\s*month|/m\b|monthly|mo\b", t))
    per_year = bool(re.search(r"per\s*(year|annum)|/y\b|/yr\b|annual|yearly|k\s*$", t))
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
    if lo < 1000 and ("k" in t or (hi < 1000 and not per_hour and not per_month)):
        lo, hi = lo * 1000, hi * 1000
    cur = "USD"
    if "€" in t or "eur" in t:
        cur = "EUR"
    if "£" in t or "gbp" in t:
        cur = "GBP"
    if per_hour:
        lo, hi = lo * 160, hi * 160
        period = "mensual (desde hourly)"
    elif per_year or lo > 20000:
        lo, hi = lo / 12, hi / 12
        period = "mensual (desde annual)"
    else:
        period = "mensual"
    return {"min": round(lo), "max": round(hi), "currency": cur, "period": period, "raw": str(raw)[:70]}


def salary_marker(parsed, salary_cfg):
    """🔴 por debajo del mínimo · 🟡 límite · 🟢 cumple objetivo · ⚪ sin dato."""
    if not parsed:
        return {"marker": "⚪", "label": "sin salario publicado", "ok": None}
    lo = parsed["min"]
    target = salary_cfg.get("target_min", 1300)
    floor = salary_cfg.get("floor", 1000)
    if lo >= target:
        return {"marker": "🟢", "label": f"cumple objetivo (${lo:,}/mes)", "ok": True}
    if lo >= floor:
        return {"marker": "🟡", "label": f"aceptable (${lo:,}/mes)", "ok": True}
    return {"marker": "🔴", "label": f"bajo mínimo (${lo:,}/mes)", "ok": False}


def latam_score(job):
    loc = (job.get("location") or "").lower()
    if not loc:
        return 1.0
    if any(x in loc for x in ("europe", "united kingdom", "uk ")) and "america" not in loc:
        return 0.5
    if any(x in loc for x in ("united states", "usa")) and "worldwide" not in loc:
        return 0.6
    return 1.0



# ---------------------------------------------------------------------------
# tracks ampliados: voice/audio, IA content, administrativo básico
# ---------------------------------------------------------------------------

VOICE_KW = ["voice", "voice over", "voiceover", "voice actor", "voice recording",
            "voice recording for ai", "voice data", "narration", "narrator",
            "audiobook", "audiobooks", "tts", "text to speech", "speech",
            "read", "reading", "storytelling", "audio content", "podcast",
            "dubbing", "subtitl", "transcription", "transcriber", "caption",
            "annotation", "annotator", "data labeling", "data labelling",
            "training data", "prompt", "prompting", "evaluation", "evaluator",
            "audio", "sound", "recording", "voice training", "vocal"]

AI_CONTENT_KW = ["ai image", "ai video", "image generation", "image editing",
                 "video editing", "video generation", "generative ai", "midjourney",
                 "stable diffusion", "ai tools", "content creation", "content creator",
                 "prompt engineering", "prompt engineer", "chatgpt", "claude",
                 "copywriting", "script", "scripts", "storyboard", "visual content",
                 "creative content", "shorts", "youtube", "reels", "tiktok",
                 "photography", "photo editing", "creative", "design", "graphic",
                 "multimedia", "video", "image", "creative ai"]

ADMIN_KW = ["data entry", "administrative assistant", "admin assistant", "virtual assistant",
            "personal assistant", "office assistant", "scheduling", "calendar management",
            "inbox management", "email management", "bookkeeping", "invoicing",
            "record keeping", "filing", "spreadsheet", "excel", "google sheets",
            "customer records", "order processing", "back office", "documentation",
            "reception", "secretary", "administrative support", "data management",
            "database", "reporting", "transcription", "typing", "data processing"]


# ---------------------------------------------------------------------------
# carriles con pesos (suman 100)
# ---------------------------------------------------------------------------

PRIORITY_HANDICAP = 12  # puntos de ventaja para tracks principales (crypto/fintech/support)
CREATIVE_ROLE_BLOCK = re.compile(
    r"\b(video editor|video editing|video editor specialist|video editing specialist|"
    r"graphic designer|graphic design|motion designer|motion graphics|ux designer|"
    r"ui designer|product designer|brand designer|illustrator|3d artist|3d designer|"
    r"sound designer|audio engineer|video producer|video production|editor for video|"
    r"video post[- ]production)\b", re.I)

# PAGO INESTABLE (lo que NO sirve): por proyecto suelto, gigs de una vez,
# comisión pura, por tarea. "Freelance" o "contractor" SOLOS no bloquean:
# un contrato freelance/contractor con pago mensual estable es aceptable.
PER_PROJECT_RE = re.compile(
    r"\b(per project|project[- ]based|per gig|one[- ]time|per task|piece work|"
    r"100% commission|commission[- ]only|paid per (project|task|gig|word|page|recording)|"
    r"pay[- ]per|per assignment|short[- ]term gig)\b", re.I)
HOURLY_RE = re.compile(r"\b(per hour|hourly|per hr|/hr\b|by the hour)\b", re.I)
# PRESENCIA FÍSICA OBLIGATORIA (no puede: vive en Paraguay, no viaja)
IN_PERSON_RE = re.compile(
    r"\b(onboard(ing)? (in person|on[- ]site|at our office|in one of our offices)|"
    r"in[- ]person onboarding|on[- ]site onboarding|must (attend|complete|do) onboarding|"
    r"onboarding (is|will be) (in person|on[- ]site|at our)|"
    r"physical office|our offices (in|are)|relocat\w* required|must relocat\w*|"
    r"must (work|be|come) (from|in|at|into) (the )?office|work from (the )?office|"
    r"office (attendance|presence|presencial)|in[- ]office (requirement|days|attendance)|"
    r"required to (be|work|come) (in|at|into) (the )?office|come into the office)\b", re.I)

# HÍBRIDO / PRESENCIA PARCIAL: no bloquea del todo pero nunca verde
HYBRID_RE = re.compile(
    r"\bhybrid\b|on[- ]site (days|requirement)|in[- ]office (days|requirement)|"
    r"office[- ]based|presencial (days|requirement)|work from office (days|some)", re.I)

# señales POSITIVAS de relación estable (empleo o contrato largo)
CONTRACT_OK_RE = re.compile(
    r"\b(contract|contractor|independent contractor|long[- ]term|ongoing|"
    r"full[- ]time|full time|permanent|monthly (salary|rate|retainer)|fixed monthly|"
    r"regular (income|work|schedule)|stable|recurring|aut[oó]nomo|contratista)\b", re.I)
BONUS_RE = re.compile(r"\b(bonus|commission|incentive|ote\b|performance[- ]based)\b", re.I)

TRACKS = {
    "crypto_support": {
        "label": "Crypto Support", "persona": "crypto_support", "priority": 1,
        "weights": {"crypto": 22, "support": 20, "english": 10, "remote": 10, "latam": 8,
                    "salary": 12, "tools": 6, "seniority": 6, "spanish": 6}},
    "crypto_operations": {
        "label": "Crypto Operations", "persona": "crypto_operations", "priority": 1,
        "weights": {"crypto": 20, "fintech": 14, "support": 8, "english": 10, "remote": 10,
                    "latam": 8, "salary": 12, "tools": 6, "seniority": 6, "spanish": 6}},
    "community": {
        "label": "Web3 Community", "persona": "community", "priority": 1,
        "weights": {"community": 24, "crypto": 12, "support": 6, "english": 10, "remote": 10,
                    "latam": 8, "salary": 12, "tools": 6, "seniority": 6, "spanish": 6}},
    "junior_research": {
        "label": "Junior Research", "persona": "junior_research", "priority": 1,
        "weights": {"research": 28, "crypto": 14, "english": 10, "remote": 10, "latam": 8,
                    "salary": 12, "tools": 6, "seniority": 6, "spanish": 6}},
    "trading_entry": {
        "label": "Crypto Trading (Entry/Junior)", "persona": "trading_entry", "priority": 1,
        "weights": {"trading": 30, "crypto": 14, "research": 8, "english": 10, "remote": 10,
                    "latam": 8, "salary": 10, "tools": 4, "seniority": 10, "spanish": 6}},
    "customer_support": {
        "label": "Customer Support", "persona": "customer_support", "priority": 1,
        "weights": {"support": 30, "fintech": 10, "english": 12, "remote": 10, "latam": 8,
                    "salary": 12, "tools": 6, "seniority": 6, "spanish": 6}},
    "operations": {
        "label": "Operations", "persona": "crypto_operations", "priority": 1,
        "weights": {"ops": 22, "fintech": 12, "support": 8, "english": 10, "remote": 10,
                    "latam": 8, "salary": 12, "tools": 6, "seniority": 6, "spanish": 6}},
    "voice_audio": {
        "label": "Voice & AI Audio", "persona": "voice_ai", "priority": 2,
        "weights": {"voice": 32, "english": 12, "spanish": 10, "remote": 10, "latam": 8,
                    "salary": 12, "seniority": 8, "tools": 4, "support": 4}},
    "ai_content": {
        "label": "AI Content / Creative", "persona": "ai_content", "priority": 2,
        "weights": {"ai_content": 28, "english": 10, "spanish": 8, "remote": 10, "latam": 8,
                    "salary": 12, "seniority": 8, "tools": 8, "support": 4, "crypto": 4}},
    "admin_ops": {
        "label": "Admin / VA Básico", "persona": "admin_ops", "priority": 2,
        "weights": {"admin": 30, "english": 10, "spanish": 8, "remote": 10, "latam": 8,
                    "salary": 12, "seniority": 8, "tools": 8, "support": 6}},
}

# Regla dura: títulos técnicos de ingeniería/desarrollo que NO corresponden
# al perfil (no defendibles en entrevista). Se marcan IGNORE directo.
TECH_TITLE_BLOCK = re.compile(
    r"\b(software|frontend|front-end|backend|back-end|full[- ]?stack|devops|sre|"
    r"platform|data|machine learning|\bml\b|\bai\b|smart contract|solidity|rust|"
    r"golang|java|python|react|node|qa|test|ios|android|mobile|security|cloud|"
    r"embedded|quant|infrastructure|network|php|wordpress|web|blockchain)\b"
    r".{0,25}\b(engineer|developer|programmer|scientist|architect)\b", re.I)

# Regla dura: senioridad alta sin marca junior -> nunca APPLY
SENIOR_TITLE = re.compile(
    r"\b(senior|lead|principal|staff|director|head of|chief)\b", re.I)
JUNIOR_TITLE = re.compile(
    r"\b(junior|entry|graduate|trainee|intern|associate)\b", re.I)
MANAGER_TECH = re.compile(
    r"\bmanager\b.{0,20}\b(technical|support|operations|team|office|program|"
    r"project|engineering|department)\b", re.I)

# Regla dura: títulos de trading con seniority alta o que piden experiencia
# avanzada -> IGNORE directo. El candidato es entry/junior, no senior trader.
# Cubre: Senior/Lead/Head/Principal/Chief Trader, "Experienced Trader",
# "Professional Trader", "Trading Manager/Director/Head of Trading", etc.
SENIOR_TRADER_TITLE = re.compile(
    r"\b(senior|lead|head of|principal|chief|experienced|professional|"
    r"senior level|expert|advanced|seasoned|proven)\b[^,]{0,30}\b(trader|trading)\b|"
    r"\b(trader|trading)\b[^,]{0,30}\b(senior|lead|head|principal|chief|"
    r"experienced|professional|manager|director|expert|advanced)\b|"
    r"\bhead of trading\b|\blead trader\b|\bchief trader\b|"
    r"\bproprietary trader\b|\bprop trader\b|"
    r"\b(senior|lead|head)\b[^,]{0,15}\bquant\b", re.I)

# Regla dura de ubicación: solo remoto GLOBAL (para poder aplicar desde Paraguay)
REMOTE_WORDS = re.compile(
    r"\b(remote|worldwide|global|anywhere|distributed|work from home|wfh|"
    r"100% home|work-at-home)\b", re.I)
LOCATION_SAFE = re.compile(
    r"\b(worldwide|global|anywhere|latin america|latam|south america|americas)\b", re.I)
LOCATION_COUNTRY = re.compile(
    r"\b(united states|usa|u\.s\.|uk|germany|france|spain|italy|netherlands|"
    r"poland|portugal|greece|cyprus|czech|canada|philippines|singapore|australia|"
    r"taiwan|pakistan|brazil|mexico|colombia|argentina|chile|peru|uruguay|india|"
    r"japan|sweden|norway|denmark|finland|ireland|switzerland|austria|belgium|"
    r"china|south korea|malaysia|indonesia|thailand|vietnam|turkey|israel|dubai|"
    r"uae|saudi|qatar|europe|emea|asia|australia|singapore)\b", re.I)


REQ_HEADER_RE = re.compile(
    r"\b(requirements?|qualifications?|what you (need|bring)|you (must|should|need) (have|be)|"
    r"what we (need|require|look for)|key requirements|essential (requirements|criteria)|"
    r"required qualifications|job requirements)\b\s*:?",
    re.I)
REQ_END_RE = re.compile(
    r"\b(benefits?|compensation|salary|what we offer|perks|about us|how to apply|"
    r"to apply|apply now|our company|company (info|description)|nice to have|"
    r"bonus points|perks & benefits)\b",
    re.I)


def _extract_requirements(desc):
    """Devuelve el texto de la sección Requirements si existe."""
    if not desc:
        return ""
    m = REQ_HEADER_RE.search(desc)
    if not m:
        return ""
    start = m.end()
    end = REQ_END_RE.search(desc, start)
    section = desc[start:end.start()] if end else desc[start:start + 1500]
    return section


def _hard_filters(job, title, text, loc):
    """Aplica reglas duras. Devuelve (nuevo_score_max, band_forced).
    band_forced: None (normal), 'IGNORE' o 'REVIEW'."""
    hay = f"{title} {loc} {text[:800]}"
    req = _extract_requirements(job.get("description") or "")
    cap = 100
    # 0) bloquear roles creativos/edición profesionales (no defendibles)
    if CREATIVE_ROLE_BLOCK.search(title):
        return 0, "IGNORE"
    # 1) bloquear títulos de desarrollo/ingeniería
    if TECH_TITLE_BLOCK.search(title):
        return 0, "IGNORE"
    # 1b) bloquear títulos de trading senior/experienced (candidato es entry-level)
    if SENIOR_TRADER_TITLE.search(title):
        return 0, "IGNORE"
    # 1c) bloquear ofertas en idiomas que el candidato NO habla
    #     (alemán, francés, italiano, portugués). El candidato habla
    #     inglés y español nativo, cualquier otro idioma es IGNORE.
    full_desc = job.get("description") or ""
    if is_unsupported_language(full_desc):
        return 0, "IGNORE"
    # 2) senioridad alta sin junior: máximo REVIEW
    if SENIOR_TITLE.search(title) and not JUNIOR_TITLE.search(title):
        cap = min(cap, 65)
    # 3) cualquier título con "manager": máximo REVIEW (no defendible)
    if re.search(r"\bmanager\b", title, re.I):
        cap = min(cap, 65)
    # 4) no es remoto en absoluto: IGNORE
    if not REMOTE_WORDS.search(hay):
        return 0, "IGNORE"
    # 4b) presencia física obligatoria (onboarding en persona, oficina, relocación)
    if IN_PERSON_RE.search(text) or IN_PERSON_RE.search(req):
        return 0, "IGNORE"
    # 4c) híbrido/presencia parcial (in-office days): EXCLUIDO TOTAL.
    #     El candidato vive en Paraguay y necesita 100% remoto.
    if HYBRID_RE.search(text) or HYBRID_RE.search(req):
        return 0, "IGNORE"
    # 5) restricción geográfica (ubicación o descripción): IGNORE directo.
    #    Solo remoto GLOBAL / LATAM / Sudamérica / Paraguay sirve.
    if _location_restricted(loc, text, title) or _location_restricted("", req, ""):
        return 0, "IGNORE"
    # requisitos de horario/ubicación estrictos en requirements
    if re.search(r"\b(must|required|need to|only) (be|work|live|based) (in|within|during)\b", req, re.I):
        cap = min(cap, 65)
    # pago inestable (por proyecto/gig/comisión pura): nunca verde
    if PER_PROJECT_RE.search(hay):
        cap = min(cap, 65)
    # pago por hora: puede ser contrato estable a tiempo completo, pero no APPLY NOW
    if HOURLY_RE.search(hay):
        cap = min(cap, 75)
    return cap, None


# países/regiones que NO incluyen Paraguay (no sirven)
_COUNTRY_RE = re.compile(
    r"\b(united states|usa|u\.?s\.?a?\.?|uk|united kingdom|england|europe|eu|emea|"
    r"canada|australia|asia|apac|india|philippines|brazil|mexico|colombia|argentina|chile|"
    r"peru|uruguay|germany|france|spain|netherlands|poland|portugal|ireland|sweden|norway|"
    r"denmark|finland|switzerland|austria|belgium|singapore|japan|south korea|malaysia|"
    r"indonesia|thailand|vietnam|turkey|israel|dubai|uae|saudi|qatar|new zealand|"
    r"china|hong kong|taiwan)\b", re.I)

# zonas SEGURAS (Paraguay incluido)
_SAFE_RE = re.compile(
    r"\b(worldwide|global|globally|anywhere|around the world|all over the world|"
    r"latin america|latam|south america|central america|americas|"
    r"ecuador|bolivia|venezuela|panama|guatemala|honduras|nicaragua|el salvador|"
    r"costa rica|dominican republic|puerto rico|cuba)\b", re.I)

# frases de restricción que suelen ir en la descripción
_RESTRICT_PATTERNS = [
    r"\b(must|need to|required to|requires|should|have to) (be )?(based|located|resident|"
    r"domiciled|physically located) (in|within)\b",
    r"\bbased (in|within)\b",
    r"\b(must|need to|required to) be (in|within)\b",
    r"\b(open|available) (only )?to (candidates|applicants) (based|located )?(in|within)\b",
    r"\bcandidates (must|need|required) (to )?be (based|located) (in|within)\b",
    r"\b(work authorization|right to work|eligib\w+ to work|authorized to work|"
    r"permit to work|visa sponsorship|work permit|visa) (in|within|required|needed|from|of|for|to work)\b",
    r"\bin possession of a (work permit|visa)\b",
    r"\b(will|shall) not be considered\b",
    r"\b(will|shall) not (be )?(considered|eligible|qualif\w+)\b",
    r"\b(must|need to|required to|have to) (have|hold|possess|obtain) a (work permit|visa|residence|permit)\b",
    r"\b(must|need to|required to) (be|have) (a|the) (citizen|resident|national|permanent resident) (of|in)\b",
    r"\b(citizens?|residents?|nationals?) of (the )?(us|usa|uk|canada|australia|germany|france|spain|"
    r"netherlands|poland|portugal|ireland|sweden|singapore|japan|india|philippines|finland|norway|denmark)\b",
    r"\b(only|exclusively) (open|available|consider\w*) (to|for)\b.{0,30}\b(candidates|applicants|"
    r"residents|based|located|citizens|nationals)\b",
    r"\b(us|usa|uk|eu|europe|canada|australia|germany|france|spain|netherlands|poland|"
    r"portugal|ireland|sweden|singapore|japan|india|philippines|brazil|mexico|argentina|"
    r"chile|colombia|peru|uruguay|finland|norway|denmark|austria|belgium|switzerland)\b"
    r"[^.]{0,40}\b(only|exclusively|required|permit|visa)\b",
]


_NO_TILDES = str.maketrans(
    {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n",
     "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U", "Ñ": "N"})


def _loc_norm(s):
    return (s or "").translate(_NO_TILDES)


def _location_restricted(loc, text, title):
    """True si la oferta NO se puede tomar desde Paraguay/remoto global.
    El campo de ubicación manda: si dice un país/región sin remoto global,
    se descarta aunque la descripción mencione 'global'."""
    loc = _loc_norm(loc or "")
    # 0) el título también puede decir "Remote - Canada, UK, Spain..." o "(USA only)"
    title_norm = _loc_norm(title)
    if _COUNTRY_RE.search(title_norm) and not _SAFE_RE.search(title_norm):
        return True
    # 1) ubicación autoritativa
    if _COUNTRY_RE.search(loc):
        return not _SAFE_RE.search(loc)
    # 2) la descripción puede esconder restricciones (escaneo COMPLETO)
    hay = f"{_loc_norm(text[:7000])} {title_norm}"
    for pat in _RESTRICT_PATTERNS:
        m = re.search(pat, hay, re.I)
        if m:
            ctx = hay[m.start():m.end() + 60]
            if _COUNTRY_RE.search(ctx) and not _SAFE_RE.search(ctx):
                return True
    return False


BANDS = [
    (90, "APPLY NOW", "🔥"),
    (75, "APPLY", "🟢"),
    (60, "REVIEW", "🟡"),
    (0, "IGNORE", "⚪"),
]


def _component(kind, title, text, parsed, salary_cfg, job):
    if kind == "crypto":
        return _kw_count(text, CRYPTO_KW, title, 3.5, 9)
    if kind == "support":
        return _kw_count(text, SUPPORT_KW, title, 3.5, 9)
    if kind == "community":
        return _kw_count(text, COMMUNITY_KW, title, 3.5, 8)
    if kind == "research":
        return _kw_count(text, RESEARCH_KW, title, 3.5, 9)
    if kind == "trading":
        return _kw_count(text, TRADING_KW, title, 3.5, 9)
    if kind == "fintech":
        return _kw_count(text, FINTECH_KW, title, 3.5, 8)
    if kind == "ops":
        return _kw_count(text, OPS_KW, title, 3.5, 8)
    if kind == "voice":
        return _kw_count(text, VOICE_KW, title, 3.5, 9)
    if kind == "ai_content":
        return _kw_count(text, AI_CONTENT_KW, title, 3.5, 9)
    if kind == "admin":
        return _kw_count(text, ADMIN_KW, title, 3.5, 9)
    if kind == "tools":
        return min(1.0, _kw_count(text, TOOLS_KW, title, 1.0, 4))
    if kind == "english":
        return 1.0 if is_english(text) else 0.5
    if kind == "spanish":
        return 1.0 if SPANISH_RE.search(text) else 0.85
    if kind == "remote":
        return 1.0 if "remote" in (job.get("location") or "").lower() or "remote" in text[:600] else 0.4
    if kind == "latam":
        return latam_score(job)
    if kind == "salary":
        if not parsed:
            return 0.5
        lo = parsed["min"]
        target = salary_cfg.get("target_min", 1300)
        floor = salary_cfg.get("floor", 1000)
        return 1.0 if lo >= target else (0.7 if lo >= floor else 0.3)
    if kind == "seniority":
        if re.search(r"\b(junior|entry|graduate|trainee|intern|associate)\b", title, re.I):
            return 1.0
        if re.search(r"\b(senior|lead|head of|principal|staff|director)\b", title, re.I):
            return 0.4
        return 0.8
    return 0.5


def score_offer(job, profile, personas=None, top_n=None):
    """
    Puntúa una oferta en todos los carriles. Devuelve:
      {score, band, emoji, track, track_label, persona, salary_parsed,
       salary_marker, breakdown[], reasons[], matched[]}
    """
    salary_cfg = profile.get("salary", {})
    title = (job.get("title") or "").lower()
    text = " ".join([
        title,
        " ".join(job.get("tags") or []),
        (job.get("description") or "")[:7000],
    ]).lower()
    parsed = parse_salary(job.get("salary") or "")
    marker = salary_marker(parsed, salary_cfg)

    best = None
    for tid, cfg in TRACKS.items():
        tot_w = sum(cfg["weights"].values())
        comps = {}
        total = 0.0
        for kind, w in cfg["weights"].items():
            c = _component(kind, title, text, parsed, salary_cfg, job)
            comps[kind] = c
            total += w * c
        score = round(100.0 * total / tot_w)
        # los tracks secundarios compiten con handicap (nunca roban prioridad)
        compare = score - (PRIORITY_HANDICAP if cfg.get("priority", 1) == 2 else 0)
        if best is None or compare > best["compare"]:
            best = {"track": tid, "score": score, "compare": compare, "comps": comps,
                    "label": cfg["label"], "persona": cfg["persona"]}

    # reglas duras (bloqueo de roles técnicos, senioridad, ubicación)
    loc = (job.get("location") or "")
    cap, forced = _hard_filters(job, title, text, loc)
    # piso salarial duro: publicado por debajo de $1.000 -> nunca verde
    if parsed and parsed["min"] < salary_cfg.get("floor", 1000):
        cap = min(cap, 65)
    if forced == "IGNORE" or best["score"] > cap:
        best["score"] = min(best["score"], cap)

    band = "IGNORE"
    emoji = "⚪"
    for thr, b, e in BANDS:
        if best["score"] >= thr:
            band, emoji = b, e
            break
    if forced == "IGNORE":
        band, emoji = "IGNORE", "⚪"

    # desglose y motivos (solo componentes con peso > 0)
    weights = TRACKS[best["track"]]["weights"]
    breakdown = []
    reasons = []
    for kind, c in best["comps"].items():
        w = weights.get(kind, 0)
        if w <= 0:
            continue
        pts = round(w * c)
        breakdown.append({"criterion": kind, "points": pts, "max": w, "pct": c})
        if c >= 0.8:
            reasons.append(f"{kind} ✓")
        elif c <= 0.35 and kind in ("crypto", "support", "research", "community", "fintech", "ops"):
            reasons.append(f"{kind} débil")
    if parsed and parsed["min"] >= salary_cfg.get("target_min", 1300):
        reasons.append("salario al objetivo")
    elif parsed:
        reasons.append(f"salario {marker['marker']}")
    if BONUS_RE.search(text):
        reasons.append("bonus/comisiones ✓")
    if CONTRACT_OK_RE.search(text):
        reasons.append("contrato estable ✓")

    return {
        "score": best["score"],
        "band": band,
        "emoji": emoji,
        "track": best["track"],
        "track_label": best["label"],
        "persona": best["persona"],
        "salary_parsed": parsed,
        "salary_marker": marker,
        "breakdown": sorted(breakdown, key=lambda x: -x["max"])[:8],
        "reasons": reasons[:6],
        "matched": [],
    }


def family_match(job, profile):
    """Keywords del perfil presentes en la oferta (para CV)."""
    text = " ".join([job.get("title", ""), " ".join(job.get("tags") or []),
                     (job.get("description") or "")[:3000]]).lower()
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


# ---------------------------------------------------------------------------
# keywords calientes del mercado (para LinkedIn/CV)
# ---------------------------------------------------------------------------

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
develop developing development manage managing management provide provides providing
require requires responsible help helps helping look looking find found get gets got give
gives take takes bring brings come comes grow growing learn learning would could will shall
may might must do does did done welcome welcoming interested interesting opportunity
opportunities career careers hiring hire hired recruit recruiting search searching seeking
immediate start starts starting player dynamic fast paced pace environment environments
culture collaborative collaboration flexible flexibility competitive benefit perks paid
vacation holiday holidays equity stocks stock bonus bonuses insurance healthcare medical
dental vision 401k pension retirement time off pto health wellness wellbeing remote
remotework distributed stakeholders stakeholder ongoing daytoday day-to-day handson
hands-on problemsolve problem-solving problemsolving selfstarter self-starter
detailoriented detail-oriented everyone everything something nothing anything always
usually often sometimes never ever really quite pretty fairly highly extremely very nice
cool awesome amazing fantastic incredible outstanding exceptional remarkable build builds
built building people lead leaded partner partners mission technology scale com url und
every success enterprise end different level levels clients client best http https www
drive not products businesses impact future real financial project large multiple various
following especially particularly additionally moreover furthermore however therefore
somos empresa puesto cargo remoto trabajo oferta vacante aplica aplicar requisitos
experiencia años habilidades equipo persona personas buscar buscamos busco necesitamos
salario ingles español idioma ventaja deseable excluyente jornada tiempo completo el la
los las de del para con sin por que se su sus un una al lo en y o a e u como cómo también
más menos entre sobre bajo durante después antes luego hasta desde porque cual cuales
quien quienes ser estar haber tener hacer puede pueden podrá podría deben debe vení veni
sumate sumar sumamos crecer creciendo desarrollar desarrollo gestión gestionar liderar
líderes nuestro nuestra nuestros nuestras tu tus mi mis
""".split())

WORD_RE = re.compile(r"[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ]{3,}")


def tokenize(text):
    return [w for w in WORD_RE.findall((text or "").lower()) if w not in STOPWORDS]


def hot_keywords(jobs, top=40):
    counter = Counter()
    for j in jobs:
        counter.update(tokenize(" ".join([j.get("title") or "",
                                          " ".join(j.get("tags") or []),
                                          (j.get("description") or "")[:1200]])))
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
