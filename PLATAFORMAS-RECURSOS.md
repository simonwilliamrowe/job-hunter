# 🌍 Plataformas y recursos para tu búsqueda — verificado el 10/08/2026

> Cada plataforma de este documento fue **probada en vivo hoy** (con `curl`) o
> está **ya integrada** en Job Hunter. "Sin penalización" = API pública oficial
> o RSS legítimo, sin violar términos de servicio, sin riesgo de baneo.

---

## 1. Cómo entender la "penalización"

| Tipo de acceso | ¿Penalización? | Ejemplos |
|---|---|---|
| **API pública oficial** (con o sin key gratis) | ✅ Ninguna — es para eso | Todas las de la sección 2 y 3 |
| **RSS oficiales** | ✅ Ninguna | We Work Remotely, Python.org |
| **APIs de pago** | ⚠️ Ninguna si pagás | Indeed, ZipRecruiter, Google Jobs (SerpApi) |
| **Scraping de páginas web** | 🚫 Riesgo real (baneo de IP/cuenta) | LinkedIn, Workday, Glassdoor, Google for Jobs directo |
| **Automatizar postulaciones** | 🚫 Baneo garantizado de cuenta | LinkedIn Easy Apply, Workday, Greenhouse (lado aplicación) |

**Regla que usamos:** solo consumir lo que las plataformas ofrecen públicamente.
Consumir APIs oficiales es legal y estable; scraping agresivo es la vía al baneo.

---

## 2. YA integradas en Job Hunter (7 fuentes, ~578 ofertas activas)

| Plataforma | Tipo | Notas |
|---|---|---|
| **Himalayas** | API pública | 🏆 La joya: +100.000 ofertas remotas, filtro `remote=true`, salarios publicados |
| **We Work Remotely** | RSS oficial | 326 ofertas activas, categorías por rol |
| **Jobicy** | API pública | 100 ofertas, sin key |
| **Remotive** | API pública | 20 ofertas curadas, tags de categoría |
| **Arbeitnow** | API pública | Remotas de Europa (suelen aceptar LATAM en remoto) |
| **Python.org Jobs** | RSS oficial | Solo remotos, filtrado |
| **RemoteOK** | API pública | Hoy 99% contaminada de spam → filtro estricto (solo con salario) |

---

## 3. VERIFICADAS HOY en vivo ✅ — listas para integrar

### 3a. APIs de los ATS más usados (la mina de oro)
Estos son los **sistemas de postulación** que usan miles de empresas. Sus APIs
de vacantes son **públicas y abiertas** (pensadas para que cualquiera las
consulte). Probadas hoy:

| ATS | Endpoint probado | Resultado |
|---|---|---|
| **Greenhouse** | `boards-api.greenhouse.io/v1/boards/{empresa}/jobs` | ✅ 189 vacantes (GitLab) |
| **Lever** | `api.lever.co/v0/postings/{empresa}?mode=json` | ✅ 388 postings (demo) |
| **Ashby** | `api.ashbyhq.com/posting-api/job-board/{empresa}` | ✅ 59 vacantes (Ashby) |
| **SmartRecruiters** | `api.smartrecruiters.com/v1/companies/{empresa}/postings` | ✅ 8 vacantes (prueba) |
| **Personio** | `{empresa}.jobs.personio.com/xml` | ✅ XML con vacantes |
| Recruitee | `{empresa}.recruitee.com/api/offers/` | Patrón documentado (org no encontrada en la prueba) |
| Teamtailor | `{empresa}.teamtailor.com/jobs.json` | No respondió hoy — pendiente de reverificar |

**Por qué importa:** con una lista de "empresas que usan Greenhouse/Lever/Ashby"
(se arma una sola vez) podés consultar las vacantes **directo en la fuente**,
sin intermediarios, incluyendo las que no aparecen en las bolsas grandes.
Integración propuesta: módulo `ats_boards.py` con un diccionario de
empresa → token, verificando "remote" en título/descripción/location.

### 3b. Otras APIs públicas abiertas verificadas

| Plataforma | Endpoint | Resultado | Para qué sirve |
|---|---|---|---|
| **Torre** (torre.ai) | `search.torre.co/opportunities/_search/` (POST) | ✅ 10 resultados | Mercado LATAM + global, roles tech, salarios en USD |
| **Hacker News "Who is hiring"** | `hn.algolia.com/api/v1/search?tags=ask_hn&query=Who is hiring` | ✅ API OK | Hilo mensual con **miles de ofertas tech directo de founders/CTOs** (muchas no salen en ninguna bolsa). Se parsean los comentarios |

### 3c. APIs gratuitas con registro (key gratis en minutos)

| Plataforma | Key | Cuota gratis | Notas |
|---|---|---|---|
| **Adzuna** | developer.adzuna.com (app_id + app_key, self-serve) | ~1.000 llamadas/mes | 16 países (UK/Europa fuerte), **salarios y estadísticas de mercado** (histogramas de salario por rol — oro para negociar). Descripciones en extracto [1](https://jobspipe.dev/alternatives/adzuna) [2](https://www.freeapisforyou.in/api/adzuna) |
| **Jooble** | api.jooble.org (key gratuita) | ~500 llamadas/día | Agregador grande, incluye muchas bolsas |
| **USAJobs** | developer.usajobs.gov (key + email) | 1.200 llamadas/min | Solo USA gov, pero hay roles remotos |
| Upwork API | registro de app + OAuth | cuota libre básica | Buscar contratos freelance (mientras llega el empleo fijo) |

---

## 4. NO recomendadas (muertas, rotas o con penalización)

| Plataforma | Por qué no |
|---|---|
| **LinkedIn** | Prohíbe automatización; scraping = baneo de cuenta. Usala a mano para aplicar y networking |
| **Indeed / ZipRecruiter / Monster / CareerBuilder** | API solo de pago (precios altos) |
| **Workday / SuccessFactors / iCIMS / Jobvite** | Sin API pública; automatizar = baneo |
| **Glassdoor** | Sin API; scraping bloqueado |
| **Google for Jobs** | No hay API directa; solo vía SerpApi (pago) o scraping arriesgado |
| **Stack Overflow Jobs** | Servicio cerrado en 2025 |
| **Working Nomads / Authentic Jobs / DjangoJobs** | Dominios muertos o "Coming Soon" |
| **CryptoJobsList** | Bloqueado por Cloudflare (anti-bot) |
| **Remote.co RSS / RemotePython** | Feeds rotos o HTML |
| **openai/apply** | El repo público **no existe** (404 verificado hoy) — ojo con tutoriales que lo referencian |

---

## 5. Repos de GitHub verificados (existen hoy) que valen la pena

### Para Claude Code (la pregunta de fondo: SÍ, hay skills listos)

| Repo | Qué es |
|---|---|
| [anthropics/skills](https://github.com/anthropics/skills) (⭐ oficial, ✅ 200) | Skills oficiales de Claude Code (PDF, DOCX, web scraping responsable, etc.) |
| [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) (✅ 200) | El índice de herramientas/plugins/recetas de Claude Code |
| [Paramchoudhary/ResumeSkills](https://github.com/Paramchoudhary/ResumeSkills) (✅ 200) | Skills de Claude Code para CV: **ATS optimizer, bullet writer, job-description analyzer, cover-letter generator, interview prep** [3](https://github.com/Paramchoudhary/ResumeSkills) |
| [olegvg/resume-tailor-plugin](https://github.com/olegvg/resume-tailor-plugin) (✅ 200) | Plugin Claude Code/Codex que **adapta tu CV por cada oferta** con análisis de gaps y scoring ATS [4](https://github.com/olegvg/resume-tailor-plugin) |
| [javiera-vasquez/claude-code-job-tailor](https://github.com/javiera-vasquez/claude-code-job-tailor) (✅ 200) | Sistema en YAML: escribís tu experiencia 1 vez y genera CV + carta adaptados en <60s [5](https://github.com/javiera-vasquez/claude-code-job-tailor) |

**Cómo se usa:** instalás Claude Code (gratis si tenés plan Claude Pro/Max),
entrás a la carpeta del proyecto y le pedís en lenguaje natural:
`/tailor <url de la oferta>` o "adaptá mi CV a esta oferta". Los skills se
instalan en la carpeta `.claude/skills/` del proyecto.

### Para la búsqueda en sí

| Repo | Qué es |
|---|---|
| [remoteintech/remote-jobs](https://github.com/remoteintech/remote-jobs) (✅ 200) | Lista mantenida de **empresas remote-friendly con su ATS** (Greenhouse/Lever/Ashby…) — exactamente lo que necesitamos para el módulo de la sección 3a |
| [lukasz-madon/awesome-remote-job](https://github.com/lukasz-madon/awesome-remote-job) (✅ 200) | Recursos remotos: bolsas, visas, comunidades |

---

## 6. Plan concreto propuesto (después de cargar tu CV real)

1. **Cargar tu perfil real** en `data/profile.json` (CV + LinkedIn afinado).
2. **Integrar el módulo ATS-boards**: Greenhouse + Lever + Ashby +
   SmartRecruiters + Personio con la lista de empresas del repo
   remoteintech → saltamos de ~578 a miles de ofertas directas de fuente.
3. **Integrar Torre + Hacker News "Who is hiring"** (tech puro, cero spam).
4. **Registrar key gratis de Adzuna** → ofertas UK/Europa + estadísticas de
   salario para negociar (y para calibrar tu expectativa salarial).
5. **Desplegar** en tu repo `simonwilliamrowe/job-hunter` (privado) con
   GitHub Actions + Telegram (guía en GITHUB-DEPLOY.md).
6. **Opcional potente:** instalar Claude Code con los skills de la sección 5
   para que el agente redacte/revise cada adaptación con IA (ya dejé el
   archivo `CLAUDE.md` preparado en el repo).
