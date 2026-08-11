# 🦅 Job Hunter — cazador de ofertas remotas para tu perfil

Herramienta para buscar ofertas de trabajo remoto, rankearlas contra TU perfil,
y generar por oferta un **paquete listo para postular**: CV adaptado en formato
ATS (.docx + .txt), carta de presentación y respuestas sugeridas para los
formularios de Workday/Greenhouse/Lever/Ashby.

## Lo que hace

| Función | Cómo |
|---|---|
| 🔎 Busca ofertas | RemoteOK · Remotive · Jobicy · We Work Remotely · Arbeitnow · PythonJobs · Himalayas (+100k) — APIs públicas, sin riesgo legal |
| 🎯 Rankea contra tu perfil | Match de keywords por título/tags/descripción → grade Alto / Medio / Bajo |
| 📄 CV adaptado por oferta | Reordena skills y bullets según la oferta, inyecta las keywords exactas del anuncio (solo las que son ciertas en tu perfil) |
| 🏢 Formato ATS-friendly | DOCX de una columna, Calibri, sin tablas ni gráficos + versión .txt para pegar en formularios |
| ✉️ Carta de presentación | Por oferta, con tus skills reales que matchean |
| ❓ Respuestas para formularios | Salario, experiencia, visado, preaviso, ubicación… listas para copiar |
| 📈 Optimización LinkedIn | Keywords calientes del mercado + las que faltan en tu perfil + checklist |

## Regla de oro (por diseño)

La herramienta **nunca inventa datos**. Solo reordena, reformula y enfatiza lo
que ya está en tu perfil. Un CV con skills que no tenés se detecta en la primera
entrevista técnica y quema tu nombre en el mercado. Adaptar ≠ mentir.

## Cómo usarla

1. **Abrí la app** (arriba a la izquierda, vista previa "Job Hunter").
2. **Pestaña "Mi perfil"** → completá tus datos reales (name, skills,
   experiencia en formato de bloques, salario mínimo, etc.) → Guardar.
3. **Pestaña "Ofertas"** → mirá las que tienen 🔥 "Match alto" → botón
   **"Preparar CV + carta + respuestas"**.
4. Descargá los 4 archivos y postulá: en los ATS que piden subir archivo usás
   el **.docx**; en los que piden pegar texto usás el **.txt**; la carta y las
   respuestas van en los campos del formulario.

## Modo IA (opcional, mejora la redacción)

Sin nada extra la app funciona en "modo plantillas" (muy decente). Si querés
redacciones más naturales, activá una API key:

```bash
export OPENAI_API_KEY="sk-..."      # o ANTHROPIC_API_KEY="sk-ant-..."
```

El modelo reescribe el resumen del CV y la carta para cada oferta, con reglas
estrictas anti-falsificación (solo usa datos reales de tu perfil).

## Correrla en tu máquina (opcional)

```bash
cd jobhunter
pip install -r requirements.txt
python -m uvicorn app:app --host 0.0.0.0 --port 8000
# abrí http://localhost:8000
```

Las ofertas se cachean 30 minutos en `data/jobs_cache.json`; tus datos quedan
en `data/profile.json`; los paquetes generados en `generated/`.

## Advertencias honestas

- **Ningún bot "pasa el ATS" por sí solo.** El ATS no es un muro: es un filtro
  de keywords + formato. Esto maximiza tus chances (keywords exactas del
  anuncio + formato limpio), pero la decisión final la toma un humano.
- **No automatices el envío** en LinkedIn/Workday: viola sus términos y banean
  cuentas. Postulate vos, con todo ya preparado: son 2-3 minutos por oferta.
- RemoteOK sufre ataques de spam: por eso su filtro es estricto (solo ofertas
  con salario publicado). Se auto-recupera.


## Desplegar como "app viva" (bot diario gratis)

Seguí la guía paso a paso en GITHUB-DEPLOY.md: en ~30 minutos tenés el bot
corriendo solo todos los días en GitHub Actions (gratis, sin servidor),
enviándote a Telegram el resumen de ofertas nuevas + los paquetes de CV del
top 3. Probá antes localmente con: python bot_daily.py


## Investigación de plataformas

Ver **PLATAFORMAS-RECURSOS.md** (verificado 10/08/2026): APIs públicas verificadas en vivo (Greenhouse, Lever, Ashby, SmartRecruiters, Personio, Torre, HN Who-is-hiring), APIs con key gratis (Adzuna, Jooble, USAJobs), plataformas prohibidas/muertas, y repos/skills de Claude Code.
