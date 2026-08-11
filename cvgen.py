"""
Job Hunter - Generador de paquetes por oferta usando PERSONAS (CVs
especializados) y la base de respuestas del candidato.

Regla de oro: solo se reformula/reordena lo que ya está en el perfil.
Nunca se inventan datos. La experiencia independiente crypto se presenta
SIEMPRE separada de la experiencia profesional (credibilidad, no inflación).
"""
import os
import re

from docx import Document
from docx.shared import Pt, Inches
from profile_store import load_personas

import ai


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:40] or "oferta"


def _exp_map(profile):
    m = {}
    for e in profile.get("experience", []) + profile.get("independent_experience", []):
        m[e.get("id")] = e
    return m


def _ordered_bullets(entry, text_low):
    bullets = list(entry.get("bullets", []))
    def rank(b):
        bl = b.lower()
        return 0 if any(m in bl for m in _matched_words(text_low)) else 1
    return sorted(bullets, key=rank)


def _matched_words(text_low):
    # palabras significativas de la oferta (para ordenar bullets)
    from matcher import CRYPTO_KW, SUPPORT_KW, COMMUNITY_KW, RESEARCH_KW, FINTECH_KW, OPS_KW, TOOLS_KW
    allk = set(CRYPTO_KW + SUPPORT_KW + COMMUNITY_KW + RESEARCH_KW + FINTECH_KW + OPS_KW + TOOLS_KW)
    return [k for k in allk if re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", text_low)][:12]


def _build_cv_text(profile, persona, job):
    lines = []
    lines.append(profile.get("name", ""))
    lines.append(persona.get("headline", profile.get("headline", "")))
    contact = " | ".join(x for x in [profile.get("email", ""), profile.get("phone", ""),
                                     profile.get("location", ""), profile.get("links", "")] if x)
    lines.append(contact)
    lines.append("")

    lines.append("SUMMARY")
    lines.append(persona.get("summary", profile.get("summary", "")))
    lines.append("")

    lines.append("SKILLS")
    lines.append(", ".join(persona.get("skills_order", [])))
    lines.append("")

    exp_map = _exp_map(profile)
    order = persona.get("experience_order", [])
    ordered = [e for e in order if e in exp_map]
    remaining = [eid for eid, e in exp_map.items() if eid not in order]
    ordered += remaining

    text_low = " ".join([job.get("title", ""), " ".join(job.get("tags", [])),
                         (job.get("description") or "")[:2500]]).lower()

    for eid in ordered:
        e = exp_map[eid]
        if not e:
            continue
        if e.get("section") == "independent":
            lines.append("INDEPENDENT CRYPTO / WEB3 EXPERIENCE")
        else:
            lines.append("PROFESSIONAL EXPERIENCE")
        hdr = e.get("role", "")
        if e.get("company"):
            hdr = f"{hdr} — {e['company']}"
        if e.get("dates"):
            hdr = f"{hdr} ({e['dates']})"
        lines.append(hdr)
        for b in _ordered_bullets(e, text_low):
            lines.append(f"• {b}")
        lines.append("")

    if profile.get("education"):
        lines.append("EDUCATION")
        for ed in profile["education"]:
            hdr = ed.get("degree", "")
            if ed.get("school"):
                hdr = f"{hdr} — {ed['school']}"
            if ed.get("dates"):
                hdr = f"{hdr} ({ed['dates']})"
            lines.append(hdr)
        lines.append("")

    if profile.get("certifications"):
        lines.append("CERTIFICATIONS")
        for c in profile["certifications"]:
            lines.append(f"• {c}")
        lines.append("")

    if profile.get("languages"):
        lines.append("LANGUAGES")
        for lang in profile["languages"]:
            l = lang.get("lang", "")
            if lang.get("level"):
                l = f"{l} — {lang['level']}"
            lines.append(l)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _build_docx(cv_text, path):
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.6)
        section.bottom_margin = Inches(0.6)
        section.left_margin = Inches(0.7)
        section.right_margin = Inches(0.7)
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)
    style.paragraph_format.space_after = Pt(4)

    name_done = False
    section = None
    for line in cv_text.splitlines():
        line = line.rstrip()
        if not line:
            if section:
                p = doc.add_paragraph()
                p.paragraph_format.space_after = Pt(6)
                section = None
            continue
        if not name_done:
            p = doc.add_paragraph()
            run = p.add_run(line)
            run.bold = True
            run.font.size = Pt(20)
            name_done = True
            continue
        if line.isupper() and len(line) < 40:
            section = line
            p = doc.add_paragraph()
            run = p.add_run(line)
            run.bold = True
            run.font.size = Pt(12)
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            continue
        p = doc.add_paragraph()
        if line.startswith("• "):
            p.paragraph_format.left_indent = Inches(0.25)
            run = p.add_run(line)
        else:
            run = p.add_run(line)
            if line and "—" in line:
                run.bold = True
    doc.save(path)


def _cover_letter(profile, persona, job, ai_text=None):
    if ai_text:
        return ai_text
    name = profile.get("name", "")
    contact = " | ".join(x for x in [profile.get("email", ""), profile.get("location", "")] if x)
    achievements = profile.get("achievements", [])[:3]
    ach_line = " ".join(f"• {a}" for a in achievements)
    return (
        f"{name}\n{contact}\n\n"
        f"Dear Hiring Team at {job.get('company', '')},\n\n"
        f"I'm writing to apply for the {job.get('title', '')} position. "
        f"I'm a bilingual (English/Spanish) professional based in Paraguay, fully "
        f"set up for remote work with flexible hours overlapping US/EU time zones.\n\n"
        f"My background combines 7+ years of hands-on crypto/Web3 experience — "
        f"self-custody, wallets, exchanges, DeFi, transaction troubleshooting and "
        f"community support — with direct customer-facing work supporting "
        f"200-300 users in financial products.\n\n"
        f"Selected highlights:\n{ach_line}\n\n"
        f"I'd love the chance to discuss how I can contribute to {job.get('company', '')}. "
        f"Thank you for your time and consideration.\n\n"
        f"Sincerely,\n{name}"
    )


def _answers_for(profile, job):
    """Base de respuestas del candidato + respuestas dinámicas de la oferta."""
    answers = dict(profile.get("answers", {}))
    parsed = None
    from matcher import parse_salary
    parsed = parse_salary(job.get("salary") or "")
    if parsed:
        answers["salary_expectation"] = (
            f"{profile.get('answers', {}).get('salary_expectation', '$1,300-$2,000/month.')} "
            f"(La oferta publica {parsed['raw']}.)")
    company = job.get("company", "")
    if company:
        answers["why_interested"] = (
            f"I'm excited about {company} because the role matches my core strengths "
            f"({', '.join((job.get('tags') or [])[:3]) or 'remote support/operations'}) "
            f"and I'm looking for a long-term remote position where I can contribute "
            f"from day one.")
    return answers


_QA_ORDER = [
    ("years_customer_support", "How many years of customer support experience do you have?"),
    ("crypto_experience", "Do you have crypto / Web3 experience? Describe it."),
    ("work_authorization", "Are you legally authorized to work in [country]? Do you require visa sponsorship?"),
    ("salary_expectation", "What are your salary expectations? (USD/month)"),
    ("english_proficiency", "How would you rate your English proficiency?"),
    ("spanish_proficiency", "Do you speak Spanish?"),
    ("availability", "When can you start? / What is your availability?"),
    ("notice_period", "What is your notice period?"),
    ("tools_zendesk", "Have you used Zendesk / Intercom / helpdesk tools?"),
    ("remote_experience", "How much remote work experience do you have?"),
    ("education_level", "What is your highest level of education?"),
    ("why_interested", "Why do you want to work here?"),
    ("portfolio_links", "Links to portfolio / GitHub / LinkedIn"),
]


def generate_package(profile, job, track=None, out_dir="generated"):
    """Genera el paquete completo para una oferta usando la persona del track."""
    personas = load_personas()
    from matcher import score_offer
    scoring = score_offer(job, profile, personas)
    track_id = track or scoring["track"]
    persona = personas.get(track_id, personas.get(scoring["persona"], {}))
    if not persona and scoring["persona"] in personas:
        persona = personas[scoring["persona"]]

    safe_dir = os.path.join(out_dir, job["id"])
    os.makedirs(safe_dir, exist_ok=True)

    cv_text = _build_cv_text(profile, persona, job)
    slug = _slug(job["company"])

    cv_docx = os.path.join(safe_dir, f"CV_{slug}.docx")
    _build_docx(cv_text, cv_docx)
    cv_txt = os.path.join(safe_dir, f"CV_{slug}.txt")
    with open(cv_txt, "w", encoding="utf-8") as f:
        f.write(cv_text)

    ai_cover = ai.ai_rewrite(profile, job, "cover")
    cover = _cover_letter(profile, persona, job, ai_text=ai_cover)
    cover_path = os.path.join(safe_dir, "cover_letter.txt")
    with open(cover_path, "w", encoding="utf-8") as f:
        f.write(cover)

    answers = _answers_for(profile, job)
    answers_path = os.path.join(safe_dir, "application_answers.txt")
    with open(answers_path, "w", encoding="utf-8") as f:
        for key, q in _QA_ORDER:
            if key in answers and answers[key]:
                f.write(f"Q: {q}\nA: {answers[key]}\n\n")

    return {
        "offer_id": job["id"],
        "track": track_id,
        "track_label": scoring["track_label"],
        "persona": persona.get("label", track_id),
        "score": scoring["score"],
        "band": scoring["band"],
        "emoji": scoring["emoji"],
        "files": [
            {"name": os.path.basename(cv_docx), "path": cv_docx, "kind": "CV (Word, ATS-friendly)"},
            {"name": os.path.basename(cv_txt), "path": cv_txt, "kind": "CV (texto, para formularios)"},
            {"name": "cover_letter.txt", "path": cover_path, "kind": "Carta de presentación"},
            {"name": "application_answers.txt", "path": answers_path, "kind": "Respuestas del formulario"},
        ],
        "answers": [{"question": q, "answer": answers.get(key, "")} for key, q in _QA_ORDER if answers.get(key)],
        "matched_skills": scoring.get("matched", []),
        "ai_tailored": bool(ai_cover),
    }
