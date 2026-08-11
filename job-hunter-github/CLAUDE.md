# CLAUDE.md — guía para Claude Code en este proyecto

Este archivo le explica a Claude Code (o cualquier agente) cómo trabajar con
Job Hunter. Usalo así: instalá Claude Code, entrá a esta carpeta y pedile
tareas en lenguaje natural (ej: "adaptá mi CV a la oferta de X").

## Reglas de oro (NO negociables)

1. **NUNCA inventar datos.** No agregues skills, empresas, años, logros o
   números que no estén en `data/profile.json`. La herramienta solo reordena,
   reformula y enfatiza lo que ya existe. Un CV inflado se detecta en la
   primera entrevista técnica.
2. **Keywords del anuncio:** usá las palabras exactas del anuncio SOLO si
   describen habilidades reales del candidato. El ATS puntúa coincidencia de
   términos, no sinónimos creativos.
3. **Formato ATS:** una columna, sin tablas, sin gráficos, sin encabezados/pies
   de página, fuente estándar (Calibri/Arial), secciones con nombres comunes
   (SUMMARY, SKILLS, EXPERIENCE, EDUCATION).

## Archivos clave

- `data/profile.json` — perfil maestro del candidato (skills, experiencia,
  educación, disponibilidad). Es la ÚNICA fuente de verdad.
- `data/jobs_cache.json` — caché de ofertas descargadas (no editar).
- `generated/` — paquetes por oferta: CV .docx (ATS) + .txt + carta +
  respuestas de formulario.
- `bot_daily.py` — bot diario (GitHub Actions). No requiere cambios salvo
  agregar fuentes.
- `fetchers.py` — fuentes de ofertas (cada `fetch_*` devuelve lista de dicts
  con `id, title, company, location, url, description, tags, salary, source,
  posted`).
- `cvgen.py` — generador de paquetes (CV adaptado + carta + respuestas).

## Tareas típicas que podés pedirle a Claude Code

### 1. Adaptar CV a una oferta puntual
```
Analizá la oferta en <URL> y el perfil en data/profile.json. Generá el paquete
con cvgen.generate_package() y revisá que:
- las skills del anuncio estén ordenadas primero (solo si son reales del perfil)
- el summary mencione las keywords relevantes
- la carta destaque 2-3 logros concretos del perfil que matcheen
No inventes nada. Si el anuncio pide algo que no está en el perfil, decilo
explícitamente en un archivo gaps.txt (para que el candidato decida).
```

### 2. Revisar/mejorar el perfil maestro
```
Revisá data/profile.json contra las ofertas en la caché (data/jobs_cache.json):
1. ¿Qué keywords calientes del mercado faltan en skills? Listalas.
2. ¿Los bullets de experiencia son medibles (números, %)? Sugerí mejoras
   manteniendo la verdad.
3. ¿El summary tiene las keywords del headline?
Escribí el análisis en profile-review.md.
```

### 3. Responder preguntas difíciles de formularios
```
Estoy aplicando a <empresa> para <puesto>. Dadas las respuestas tipo en
generated/<id>/application_answers.txt y mi perfil, escribime una versión
más personalizada de "Why do you want to work here?" basada en datos reales
del perfil y en lo que la empresa hace (verificá su sitio web).
```

### 4. Mantener las fuentes
```
Agregá una nueva fuente de ofertas a fetchers.py siguiendo el patrón de
fetch_himalayas(). Probala con: python3 -c "import fetchers; print(fetchers.fetch_NOMBRE())"
Verificá antes que el endpoint sea una API/RSS público oficial (sin scraping).
```

## Cómo correr las cosas

```bash
python3 bot_daily.py          # bot diario (resumen + paquetes top 3)
python3 -m uvicorn app:app --port 8000   # app web local
```

## Skills útiles para instalar (opcional)

- Paramchoudhary/ResumeSkills (skills de CV/ATS para Claude Code)
- olegvg/resume-tailor-plugin (adaptación por oferta con scoring ATS)
- anthropics/skills (oficiales: PDF, DOCX)

## Nota de seguridad

`data/profile.json` contiene datos personales. Nunca lo subas a repos públicos
ni lo incluyas en outputs compartidos. El repo de GitHub debe ser PRIVADO.
