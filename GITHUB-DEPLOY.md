# 🚀 Guía de despliegue — Job Hunter como app viva en GitHub (100% gratis)

Con esto, el bot **corre solo todos los días a las 07:00/08:00 de Paraguay**,
revisa 7 bolsas de trabajo remoto, filtra contra tu perfil y **te manda el
resumen + los CV preparados a tu Telegram**. No necesitás servidor, no se
apaga nunca, y es gratis.

> ⏱️ Tiempo total: ~25-30 minutos, una sola vez.

---

## ⭐ OPCIÓN MÁS FÁCIL — Subir por el navegador (sin instalar nada, ~15 min)

> Esta opción no requiere git, ni token, ni instalar programas. Todo desde el navegador.

1. **Descargá el paquete** `job-hunter-github.zip` (te lo dejé en el workspace) y **descomprimilo** en tu PC (clic derecho → Extraer aquí). Verás una carpeta con archivos `.py`, `data/`, `static/`, etc.
2. Entrá a **github.com → tu repositorio** (el privado que creaste).
3. Clic en **"Add file"** → **"Upload files"**.
4. Arrastrá adentro TODOS estos elementos (uno por uno o en bloque):
   - Los archivos sueltos: `README.md`, `GITHUB-DEPLOY.md`, `CLAUDE.md`, `requirements.txt`, `INICIAR-JOB-HUNTER.bat`, `ai.py`, `app.py`, `ats_boards.py`, `bot_daily.py`, `cvgen.py`, `fetchers.py`, `matcher.py`, `profile_store.py`, `tracker.py`
   - La **carpeta `data/`** (entera: contiene `profile.json` y `personas.json`)
   - La **carpeta `static/`** (entera: contiene `index.html`)
   - ⚠️ NO subas `data/jobs_cache.json` ni `data/seen.json` si aparecen (son caché local; el bot los crea solo).
5. Abajo, botón verde **"Commit changes"** → **"Commit directly to the main branch"** → **Commit changes**.
6. **Crear el workflow** (el paso que no se puede arrastrar): clic en **"Add file"** → **"Create new file"** → como nombre de archivo poné EXACTAMENTE:
   ```
   .github/workflows/daily-digest.yml
   ```
   (GitHub crea las carpetas solas). Pegá adentro el contenido del archivo `daily-digest.yml` que está en tu zip (lo abrís con el bloc de notas) → **Commit new file**.
7. **Configurar los secrets** (después de crear el bot de Telegram, Paso 4): en tu repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret** → agregá `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`.
8. **Probar**: pestaña **Actions** → **"Digesto diario de ofertas"** → **Run workflow** → esperá a que quede verde ✔ → revisá tu Telegram.

> ¿Preferís la vía tradicional con git? Seguí el Paso 3 de abajo (necesitás un Personal Access Token). GitHub Desktop (https://desktop.github.com) también funciona y maneja los archivos ocultos solo.

---

## Paso 0 — Creá tu email de búsqueda laboral (5 min)

Usá el email nuevo que querés dedicar al empleo (el de tu proyecto NO):

1. Creá un **Gmail nuevo**: https://accounts.google.com/signup
   - Ej: `tunombre.trabajo@gmail.com` o `tunombre.jobs@gmail.com`
2. Ese email será tu identidad de búsqueda: lo usás para GitHub, para
   postular, para LinkedIn si querés.

## Paso 1 — Creá tu cuenta de GitHub con ESE email (5 min)

1. Andá a https://github.com/signup
2. Registrate con el email nuevo del Paso 0 (username sugerido: `tunombre-jobs`)
3. Confirmá el email desde el correo que te llega.

## Paso 2 — Creá el repositorio PRIVADO (2 min)

1. En GitHub: botón verde **"New"** / **"New repository"**
2. Repository name: `job-hunter`
3. **IMPORTANTE:** marcá **Private** (🔒) — contiene tu CV con datos
   personales. NUNCA lo hagas público.
4. No marques "Add a README" ni ".gitignore" → botón **Create repository**.

## Paso 3 — Subí el código a GitHub (5 min)

1. Descargá el archivo **`job-hunter-github.zip`** que te preparé y descomprimilo
   (o usá la carpeta `jobhunter` que ya tenés).
2. Abrí una terminal en esa carpeta (Windows: clic derecho → "Abrir en Terminal";
   Mac/Linux: cd hasta la carpeta).
3. Copiá y pegá estos comandos, reemplazando `TU_USUARIO` por tu usuario de GitHub:

```bash
git init
git add .
git commit -m "Job Hunter v1"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/job-hunter.git
git push -u origin main
```

> Windows: cuando te pida usuario/contraseña, poné TU USUARIO y como contraseña
> un **Personal Access Token** (GitHub ya no acepta la contraseña normal).
> Creación del token: https://github.com/settings/tokens → "Generate new token
> (classic)" → marcar `repo` → copiar el código que empieza con `ghp_...`.

Si el push falla por tema de autenticación, la forma más fácil es instalar
**GitHub Desktop** (https://desktop.github.com), abrir sesión con tu cuenta
nueva y "Add local repository" → seleccionar la carpeta → "Publish repository"
→ marcar **Private** → Publish.

## Paso 4 — Creá el bot de Telegram (5 min)

1. Abrí Telegram y buscá **@BotFather** (es el bot oficial).
2. Enviá: `/newbot`
3. Te pide un nombre: `Job Hunter` (lo que quieras)
4. Te pide un username que termine en `bot`: `tu_nombre_jobs_bot`
5. BotFather te devuelve un **token** tipo `7234567890:AAF...`. **Guardalo.**
6. Ahora conseguí tu **chat id**:
   - Abrí el chat con tu bot nuevo y enviá cualquier mensaje (ej: `hola`)
   - En tu navegador, abrí:
     `https://api.telegram.org/bot<TU_TOKEN>/getUpdates`
   - En la respuesta, buscá `"chat":{"id":123456789` → ese número es tu chat id.
     **Guardalo.**

## Paso 5 — Configurá los secrets en GitHub (3 min)

1. En tu repo: **Settings** → **Secrets and variables** → **Actions**
2. Botón **"New repository secret"** — agregá estos dos:
   - Nombre: `TELEGRAM_BOT_TOKEN` → valor: el token del paso 4
   - Nombre: `TELEGRAM_CHAT_ID` → valor: el chat id del paso 4

## Paso 6 — Probá el bot (3 min)

1. En GitHub, pestaña **Actions** → workflow **"Digesto diario de ofertas"**
2. Botón **"Run workflow"** → **Run workflow** (se ejecuta al instante)
3. Mirá que la ejecución termine en verde (✔) y...
4. 📲 **Revisá tu Telegram**: te llega el resumen del día con las mejores
   ofertas para tu perfil + el zip con los CV adaptados del top 3.

## Paso 7 — ¡A partir de mañana corre solo! 🌅

Todos los días a las **11:00 UTC = 07:00/08:00 de Paraguay** el bot hace su
trabajo y te llega el resumen al despertar. En **Actions** podés ver el
historial de ejecuciones y los logs.

---

## Tus datos reales (IMPORTANTE)

El bot usa `data/profile.json` como perfil. Hoy tiene el **perfil de ejemplo**.

**Para poner tus datos reales:**
1. Corré la app web en tu PC (ver README → `INICIAR-JOB-HUNTER.bat`).
2. Completá la pestaña **"Mi perfil"** con tu info real → Guardar.
3. Copiá el archivo `data/profile.json` actualizado a la carpeta del repo y
   subilo:
   ```bash
   git add data/profile.json
   git commit -m "Perfil real"
   git push
   ```
4. (Opcional, sin PC) Editá `data/profile.json` directamente desde GitHub:
   archivo → ícono ✏️ → guardar → "Commit changes". Es JSON, cuidá comas y llaves.

⚠️ **Nunca pongas datos que no sean ciertos.** El bot solo reformula tu
información real; la entrevista técnica siempre confirma.

## Activar la redacción con IA (opcional)

Agregá un tercer secret en GitHub: `OPENAI_API_KEY` (una key de
https://platform.openai.com — cuesta centavos por mes) o `ANTHROPIC_API_KEY`.
El resumen del CV y las cartas se redactan mejor para cada oferta. Sin key,
funciona igual en "modo plantillas".

## Preguntas frecuentes

**¿Se postula solo?** No, a propósito. LinkedIn/Workday/Greenhouse banean
cuentas por automatización y los ATS detectan bots. Vos aplicás en 2-3 min por
oferta con todo ya preparado: esa es la estrategia que funciona.

**¿Cuánto cuesta?** Nada. GitHub Actions gratis: 2.000 minutos/mes (esto usa ~3).

**¿Y si quiero la interfaz web también en línea?** Opciones gratis:
- **Render.com**: servicio web con plan Free (se "duerme" a los 15 min de
  inactividad y despierta al visitarla — para uso personal alcanza).
- **PythonAnywhere.com**: cuenta free con 1 tarea programada diaria (podés
  correr `bot_daily.py` ahí y tu app web básica).

**¿El repo se ve público?** No: lo creaste **Private**. GitHub no muestra
repos privados a nadie.

**¿Qué pasa si un día no corre?** El bot marca "nuevas" solo lo que no vio
antes; si un día falla, al siguiente te manda lo que haya. Las ofertas se
revisan con caché de 30 min para no molestar a las bolsas.
