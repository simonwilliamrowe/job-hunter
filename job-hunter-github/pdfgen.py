"""
Job Hunter - Generador de CVs en PDF con formato visual profesional
(para adjuntar a emails, enviar por LinkedIn o imprimir).

Genera un PDF por persona: CV Maestro + los CVs especializados.
Usa el MISMO contenido veraz del perfil (nunca inventa), solo con diseño.
"""
import os
import re
import sys

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph,
                                Spacer, HRFlowable, KeepTogether)

from profile_store import load_profile, load_personas

INK = HexColor("#1d2b3a")       # texto principal
ACCENT = HexColor("#1465bb")    # azul sobrio
MUTED = HexColor("#5a6b7d")     # gris metadatos
LINE = HexColor("#c9d6e4")      # línea separadora
WHITE = HexColor("#ffffff")

W, H = A4
MARGIN = 16 * mm


def _styles():
    s = {
        "name": ParagraphStyle("name", fontName="Helvetica-Bold", fontSize=21,
                               leading=24, textColor=INK, spaceAfter=2),
        "headline": ParagraphStyle("headline", fontName="Helvetica-Bold", fontSize=11.5,
                                   leading=14, textColor=ACCENT, spaceAfter=3),
        "contact": ParagraphStyle("contact", fontName="Helvetica", fontSize=9,
                                  leading=12, textColor=MUTED, spaceAfter=6),
        "section": ParagraphStyle("section", fontName="Helvetica-Bold", fontSize=12,
                                  leading=14, textColor=ACCENT, spaceBefore=10, spaceAfter=4),
        "role": ParagraphStyle("role", fontName="Helvetica-Bold", fontSize=10.5,
                               leading=13, textColor=INK, spaceBefore=7, spaceAfter=1),
        "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=9.5,
                                 leading=12.5, textColor=INK, leftIndent=10,
                                 bulletIndent=0, spaceAfter=1.5, alignment=TA_JUSTIFY),
        "plain": ParagraphStyle("plain", fontName="Helvetica", fontSize=9.5,
                                leading=12.5, textColor=INK, spaceAfter=1.5),
    }
    return s


def _esc(t):
    return (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _add_contact(doc, profile, st):
    parts = [profile.get("email", ""), profile.get("phone", ""),
             profile.get("location", ""), profile.get("links", "")]
    parts = [p for p in parts if p]
    doc.append(Paragraph(_esc(" | ".join(parts)), st["contact"]))
    doc.append(HRFlowable(width="100%", thickness=0.8, color=LINE, spaceAfter=2))


def _add_section(doc, title, st):
    doc.append(Paragraph(_esc(title), st["section"]))
    doc.append(HRFlowable(width="100%", thickness=0.5, color=LINE, spaceAfter=3))


def _add_bullets(doc, bullets, st):
    for b in bullets:
        b = re.sub(r"^•\s*", "", b or "").strip()
        if b:
            doc.append(Paragraph(_esc(b), st["bullet"], bulletText="•"))


def build_pdf(profile, persona, out_path):
    st = _styles()
    doc = BaseDocTemplate(out_path, pagesize=A4,
                          leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=MARGIN, bottomMargin=MARGIN,
                          title=f"CV - {profile.get('name','')}",
                          author=profile.get("name", ""))
    frame = Frame(MARGIN, MARGIN, W - 2 * MARGIN, H - 2 * MARGIN, id="f")
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame])])

    story = []
    story.append(Paragraph(_esc(profile.get("name", "")), st["name"]))
    story.append(Paragraph(_esc(persona.get("headline", profile.get("headline", ""))), st["headline"]))
    _add_contact(story, profile, st)

    # SUMMARY
    _add_section(story, "SUMMARY", st)
    story.append(Paragraph(_esc(persona.get("summary", profile.get("summary", ""))), st["plain"]))

    # SKILLS
    skills = persona.get("skills_order") or []
    if skills:
        _add_section(story, "SKILLS", st)
        story.append(Paragraph(_esc(", ".join(skills)), st["plain"]))

    # EXPERIENCIA: orden de la persona
    exp_map = {}
    for e in profile.get("experience", []) + profile.get("independent_experience", []):
        exp_map[e.get("id")] = e
    order = [i for i in persona.get("experience_order", []) if i in exp_map]
    order += [i for i in exp_map if i not in order]

    last_was_independent = None
    for eid in order:
        e = exp_map[eid]
        is_ind = e.get("section") == "independent"
        if is_ind != last_was_independent:
            _add_section(story, "INDEPENDENT CRYPTO / WEB3 EXPERIENCE" if is_ind else "PROFESSIONAL EXPERIENCE", st)
            last_was_independent = is_ind
        hdr = e.get("role", "")
        if e.get("company"):
            hdr = f"{hdr} — {e['company']}"
        if e.get("dates"):
            hdr = f"{hdr} · {e['dates']}"
        block = [Paragraph(_esc(hdr), st["role"])]
        bullets = [re.sub(r"^•\s*", "", b).strip() for b in e.get("bullets", []) if b]
        for b in bullets:
            block.append(Paragraph(_esc(b), st["bullet"], bulletText="•"))
        story.append(KeepTogether(block))

    # EDUCACIÓN
    if profile.get("education"):
        _add_section(story, "EDUCATION", st)
        for ed in profile["education"]:
            hdr = ed.get("degree", "")
            if ed.get("school"):
                hdr = f"{hdr} — {ed['school']}"
            if ed.get("dates"):
                hdr = f"{hdr} · {ed['dates']}"
            story.append(Paragraph(_esc(hdr), st["plain"]))

    # CERTIFICACIONES
    if profile.get("certifications"):
        _add_section(story, "CERTIFICATIONS", st)
        for c in profile["certifications"]:
            story.append(Paragraph(_esc(c), st["bullet"], bulletText="•"))

    # LENGUAS
    if profile.get("languages"):
        _add_section(story, "LANGUAGES", st)
        for l in profile["languages"]:
            txt = l.get("lang", "")
            if l.get("level"):
                txt = f"{txt} — {l['level']}"
            story.append(Paragraph(_esc(txt), st["plain"]))

    doc.build(story)
    return out_path


def main():
    profile = load_profile()
    personas = load_personas()
    out_dir = "cvs_pdf"
    os.makedirs(out_dir, exist_ok=True)
    jobs = [
        ("CV_Maestro", None, "CV maestro — perfil completo"),
        *[(p["label"], pid, p.get("headline", "")) for pid, p in personas.items()],
    ]
    made = []
    for label, pid, _ in jobs:
        persona = personas.get(pid, {}) if pid else {}
        safe = label.replace(" ", "_").replace("(", "").replace(")", "").replace("é", "e").replace("ó", "o").replace("í", "i").replace("ú", "u").replace("ñ", "n")
        path = os.path.join(out_dir, f"{safe}.pdf")
        build_pdf(profile, persona, path)
        made.append(path)
        print("OK:", path)
    return made


if __name__ == "__main__":
    main()
