"""PDF-Steckbrief der aktuellen Einstellung (fpdf2, Kernschriften: Umlaute gehen, Gedankenstrich und Euro-Zeichen nicht)."""
from fpdf import FPDF

import stz_constants as C

_REPLACE = {"„": '"', "“": '"', "”": '"', "–": "-", "—": "-", "≈": "ca. ", "≥": ">=", "≤": "<=", "φ": "phi", "ψ": "psi", "·": "*", "…": "...", "**": "", "’": "'"}


def clean(text: str) -> str:
    for a, b in _REPLACE.items():
        text = text.replace(a, b)
    return text.encode("latin-1", "replace").decode("latin-1")


def generate_pdf(settings: dict, rows: dict, verdicts: list, runs: int) -> bytes:
    """settings: {Bezeichnung: Wert}; rows: Ergebnis von compare(); verdicts: Liste von Texten; runs: Läufe je Strategie."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.multi_cell(0, 8, clean("Sitzplatz im Zug ohne Reservierung"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, clean("Modellrechnung mit gesetzten Annahmen (keine Messung im Zug). Sebastian Hanisch - Operations Research und Machine Learning."),
                   new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Einstellungen", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for k, v in settings.items():
        pdf.cell(80, 6, clean(k))
        pdf.cell(0, 6, clean(str(v)), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, clean(f"Ergebnis ({runs} gepaarte Läufe)"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 9)
    for head, w in (("Strategie", 70), ("Sitzanteil der Fahrt", 40), ("Platz beim Einsteigen", 40), ("Weg (Reihen)", 30)):
        pdf.cell(w, 6, clean(head), border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    for k in C.APP_STRATEGIES:
        if k not in rows:
            continue
        r = rows[k]
        pdf.cell(70, 6, clean(C.STRATEGY_LABELS[k]), border=1)
        pdf.cell(40, 6, f"{100 * r['sitz']:.0f} % +- {100 * r['se']:.0f}", border=1)
        pdf.cell(40, 6, f"{100 * r['sofort']:.0f} %", border=1)
        pdf.cell(30, 6, f"{r['weg']:.0f}", border=1)
        pdf.ln()
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 10)
    for v in verdicts:
        pdf.multi_cell(0, 5.5, clean(v), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
    return bytes(pdf.output())
