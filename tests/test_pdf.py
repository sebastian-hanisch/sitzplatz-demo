"""PDF-Steckbrief: erzeugt gültiges PDF auch mit Zeichen außerhalb von Latin-1 (Kernschriften)."""

import stz_constants as C
import stz_evaluation as ev
from stz_pdf_export import clean, generate_pdf


def test_clean_replaces_characters_the_core_fonts_cannot_encode():
    assert clean("„Nächste Tür“ – ≈ 20 % φ ψ **fett**") == '"Nächste Tür" - ca.  20 % phi psi fett'
    assert clean("Äpfel, Öl, Übung, Straße") == "Äpfel, Öl, Übung, Straße"
    clean("€ ≠ ∞")  # keine Ausnahme


def test_generate_pdf_returns_a_pdf_for_the_default_setting():
    rows = {k: dict(sitz=0.5, se=0.02, sofort=0.3, weg=4.0) for k in C.APP_STRATEGIES}
    data = generate_pdf({"Spitzenlast": "120 % der Sitzplätze"}, rows, ["**Beste Strategie:** „Zugende“ – 90 %"], 40)
    assert data[:5] == b"%PDF-" and len(data) > 1500


def test_generate_pdf_from_a_live_comparison():
    rows = ev.compare(ev.Settings(), n=3)
    assert generate_pdf({"x": 1}, rows, [], 3)[:5] == b"%PDF-"
