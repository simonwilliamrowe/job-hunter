"""
Job Hunter - Integración opcional con modelos de IA (OpenAI o Anthropic).

Sin API key la herramienta funciona igual (modo plantillas + keywords).
Con API key, el summary del CV y la carta de presentación se reescriben
adaptados a cada oferta, con reglas estrictas anti-falsificación:
SOLO puede reformular datos que ya están en el perfil. NUNCA inventar.
"""
import json
import os

import requests

_SYSTEM = (
    "You are an expert resume writer helping a job applicant tailor their resume "
    "to a specific job posting. STRICT RULES: (1) NEVER invent, add, or imply "
    "skills, technologies, companies, titles, dates, numbers, or achievements that "
    "are not explicitly present in the applicant's profile data. (2) Only reword, "
    "reorder and emphasize what is already there, using exact keywords from the job "
    "posting where they truthfully apply. (3) Output plain text only, no markdown, "
    "no headers, no bullet symbols. (4) Keep it concise and natural."
)


def ai_enabled():
    return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))


def _call_openai(prompt):
    key = os.environ["OPENAI_API_KEY"]
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": "gpt-4o-mini",
            "temperature": 0.4,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def _call_anthropic(prompt):
    key = os.environ["ANTHROPIC_API_KEY"]
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-3-5-haiku-latest",
            "max_tokens": 1200,
            "temperature": 0.4,
            "system": _SYSTEM,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["content"][0]["text"].strip()


def ai_rewrite(profile, job, what):
    """
    what: 'summary' -> reescribe el resumen del CV para la oferta.
          'cover'   -> redacta carta de presentación para la oferta.
    Devuelve texto, o None si no hay API key o falla.
    """
    if not ai_enabled():
        return None
    job_txt = "\n".join([
        f"Title: {job.get('title', '')}",
        f"Company: {job.get('company', '')}",
        f"Tags: {', '.join(job.get('tags', []))}",
        f"Salary: {job.get('salary', '')}",
        f"Description: {(job.get('description') or '')[:3500]}",
    ])
    prof = {
        "name": profile.get("name"),
        "headline": profile.get("headline"),
        "summary": profile.get("summary"),
        "skills": profile.get("skills"),
        "experience": profile.get("experience"),
        "education": profile.get("education"),
        "languages": profile.get("languages"),
    }
    if what == "summary":
        task = (
            "TASK: Rewrite the applicant's SUMMARY (3-5 sentences) so it reads as "
            "tailored to this job posting, incorporating exact keywords from the "
            "posting ONLY where they match the applicant's real profile. Do not "
            "mention anything not in the profile."
        )
    else:
        task = (
            "TASK: Write a professional cover letter (150-220 words) for this "
            "applicant applying to this job. Start with 'Dear Hiring Team,' and end "
            "with 'Sincerely,' followed by the applicant's name. Reference 2-4 "
            "concrete real points from the profile. Do not invent facts."
        )
    prompt = f"JOB POSTING:\n{job_txt}\n\nAPPLICANT PROFILE:\n{json.dumps(prof, indent=1, ensure_ascii=False)}\n\n{task}"
    try:
        if os.environ.get("OPENAI_API_KEY"):
            return _call_openai(prompt)
        return _call_anthropic(prompt)
    except Exception as e:  # noqa: BLE001
        print(f"[ai] fallback a modo plantilla ({what}): {e}")
        return None
