# Sitzplatz im Zug ohne Reservierung – wohin am Bahnsteig, wenn alle dasselbe wollen? – Streamlit-Demo

<!-- TODO nach dem Deploy: direkt hierher den Live-Link setzen (Leerzeile davor und danach):
**[→ Demo live ausprobieren](https://sebastianhanisch-sitzplatz-demo.streamlit.app/)** -->

Fall-Demo für die Website „Sebastian Hanisch – Operations Research und Machine Learning“ (`demos.html`), siebter Baustein der Reihe **Bahn/Schienenverkehr** und der erste aus Sicht der **Fahrgäste**
(die sechs anderen Bausteine – Takt, Crew Pairing, Trassenkonflikt, Ablaufberg, Fahrzeitreserve, Energiefahrweise – sind Betreiberseite). Ein Fahrgast ohne Platzreservierung wählt Tür und Platzsuche in einem Zug
mit 320 Plätzen, in dem sich die Mitreisenden an den Treppen des Bahnsteigs bündeln. Verglichen werden fünf Strategien (nächste Tür, Zugende, durchlaufen, stehen bleiben, Anzeige) auf **denselben Zugverläufen**;
die Kernfrage ist, **ab welchem Anteil Mitwisser der bekannte Tipp „geh ans Zugende“ seinen Vorsprung verliert**, und ob eine Auslastungsanzeige besser dasteht.

**Alle Verhaltensparameter sind Annahmen, keine Messungen im Zug.** Die Demo sagt „im Modell, unter diesen Annahmen“, nie „im Zug ist es so“.

## Warum dieses Problem

Die Wagen an den Treppen sind voll, hinten ist es leer: Der Tipp „ans Zugende“ ist bekannt, und die Literatur schlägt vor, Wartenden die Wagenauslastung mitzuteilen, damit sie sich gleichmäßiger verteilen.
Was beides übersieht: Ein Tipp, dem alle folgen, ist kein Tipp mehr (Herdeneffekt). **Wie viele müssen ihn kennen, bevor er nichts mehr bringt?** Der Herdeneffekt selbst ist nicht neu:
[`nash-demo`](https://github.com/sebastian-hanisch/nash-demo) zeigt ihn bei der Torwahl von Lkw („alle springen zum gerade leersten Tor“), dort mit Wartezeit statt Platzschwelle.
Neu sind hier die **Kapazitätsschwelle** (Platz ja oder nein), der **Anteil der Mitwisser als Regler**, die Reichweite beim Platzsuchen und die Zeitachse mit Nachrücken an den Halten.

## Modell

Zug aus 8 Wagen zu 10 Reihen zu 4 Plätzen (320 Plätze), 16 Türen an den Wagenenden, Linie mit 10 Halten; jedes Start-Ziel-Paar bringt eine Poisson-verteilte Zahl von Fahrgästen, die Rate ist so gesetzt,
dass der stärkste Querschnitt auf die Spitzenlast kommt. Die Mitreisenden wählen eine Tür mit Treppen-Gewicht `1 + a · exp(-(d - d0)² / 2σ²)` (Zugang bei Reihe 25, σ = 15 Reihen), suchen den
nächsten freien Platz in ihrer Reichweite und stehen sonst an der Tür; Stehende rücken an jedem Halt auf frei gewordene Plätze nach (Reichweite 15 Reihen). Der Fokus-Fahrgast fährt drei Halte,
gemessen wird der **Sitzanteil** der drei Abschnitte. Ein Anteil φ der Mitreisenden folgt dem Tipp („alle an die Türen des letzten Wagens“ oder „gleichmäßig über die hintere Wagenhälfte“),
ein Anteil ψ sieht bei Einfahrt die Auslastung und wählt danach seine Tür („Alle zur besten Tür“ oder „zufällig im Verhältnis der Bewertung“). Formeln und Annahmen-Tabelle (Spalte „Wer setzt an“)
stehen in der App (📐 und 📋).

Die Zufallszahlen kommen aus einem eigenen ganzzahligen SplitMix64-Generator (`stz_rng.py`), alle Ziehungen werden vorab gezogen: gleiche Zufallszahlen für alle Strategien und über φ und ψ hinweg.

## Methodik

- **Gepaarter Strategievergleich** (`stz_runs.py`): Der Zug wird bis zum Einstiegshalt einmal gefahren und je Strategie kopiert; der Fokus-Fahrgast steigt an derselben Stelle der Einstiegsreihenfolge ein.
  Live 40 Läufe, vorgerechnet 100 (Tabellen 60).
- **Strategien:** *Nächste Tür* (wie die Mitreisenden), *Zugende* (der Tipp), *Durchlaufen* (nächste Tür, dann durch den ganzen Zug), *Stehen bleiben*, *Anzeige* (Blick bei Ankunft: Tür mit dem besten Verhältnis
  freie Plätze zu erwarteter Konkurrenz, sonst durchlaufen). Dazu ein **Orakel unter den Regeln**, das alle 16 Türen mit „sofort“, „durchlaufen“ und „stehen“ probiert (kennt den Lauf; nur Schranke, keine Strategie).
- **Kreuzungspunkt φ\***: erster Anteil, bei dem „Zugende“ nicht mehr vor „Nächste Tür“ liegt (linear interpoliert); „kein Vorteil“, wenn der Vorsprung bei φ = 0 höchstens 0,02 beträgt.
- **Messreihe** (`data/stz_results.json`, `tools/sweep_*.py`): 576 Zellen für φ\* (Bündelung × Reichweite × Spitzenlast × Einstiegshalt × Gangblockade × Tipp-Art), 64 für die Anzeige, 24 für die Strategien, 16 für das Orakel,
  32 für die Grenze der Annahme. Die App rechnet sie nie live.

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen werden in `tests/test_claims.py` aus `data/stz_results.json` nachgerechnet; dass die Datei selbst vom Kern stammt, prüft `tests/test_results.py` an Stichproben.

| Frage | Befund | Test |
|---|---|---|
| Wo kippt der Tipp „alle ans Zugende“? | In 198 von 288 Zellen hat er allein einen Vorsprung und verliert ihn bei einem Befolger-Anteil von **10 bis 30 %** (Median 19 %); nie über 60 % | `test_tip_crossing_over_288_cells_per_tip_kind` |
| Hält ein breiter Tipp länger? | Ja: verteilen sich die Befolger über die hintere Wagenhälfte, sind es 10 bis 45 % (Median 31 %) | dito |
| Was braucht der Tipp? | **Bündelung an den Treppen**: ohne sie in 72 von 72 Zellen kein Vorsprung; mit Bündelung und Spitzenlast ab 100 % in 144 von 144 Zellen ein Vorsprung (φ\* 12 bis 30 %) | `test_bundling_is_the_precondition` |
| Hilft der Tipp bei halbleerem Zug? | Selten: bei 80 % Spitzenlast hat er in 42 von 96 Zellen keinen Vorsprung (genug Plätze) | `test_low_load_often_has_no_advantage` |
| Ändert eine Gangblockade den Kreuzungspunkt? | Nein: je 45 Zellen ohne Vorsprung, Median 19 % mit und ohne Blockade; sie wirkt nur auf „Durchlaufen“ | `test_blockade_does_not_move_the_crossing` |
| Wann gibt es keinen Vorsprung mehr? | Laufen die Mitreisenden 60 bis 80 Reihen weit und die Spitzenlast ist 100 %, hat der Tipp in allen 8 Zellen keinen Vorsprung; bei 120 % bleibt er klein (79 % gegen 72 %) | `test_the_advantage_vanishes_when_everyone_walks_far` |
| Wie schneiden die Strategien allein ab? | „Zugende“, „Anzeige“ und das Orakel erreichen in allen 24 Zellen 100 %; „Durchlaufen“ 100 % ohne Gangblockade, 78 bis 100 % mit; „Stehen bleiben“ 49 bis 67 %; „Nächste Tür“ 59 bis 100 %. Das ist die Annahme des leeren Hinterzugs, kein Ergebnis | `test_strategy_table_at_zero_followers` |
| Verliert die Anzeige ihren Vorsprung? | Bei 120 % Spitzenlast: Anzeige 100 / 82 / 71 / 60 % bei ψ = 0 / 20 / 40 / 100 % gegen „Nächste Tür“ 54 / 74 / 78 / 77 %; Kreuzung bei ψ ≈ 26 %, wenn alle zur besten Tür gehen | `test_display_experiment_at_load_120` |
| Hilft Zufallswahl im Verhältnis der Bewertung? | Sie hält länger (99 / 95 / 78 / 74 % gegen 54 / 62 / 76 / 76 %); ab ψ ≈ 40 % ist der Unterschied zu „Nächste Tür“ nicht mehr vom Rauschen zu trennen (Standardfehler 2 bis 4 Pp.) | dito |
| Und bei genug Plätzen? | Bei 100 % Spitzenlast bleibt die Anzeige bei allen ψ über 97,5 % | `test_display_experiment_with_enough_seats_and_walking_through` |
| Was ist robust? | „Durchlaufen“ liegt bei 120 % Spitzenlast in allen 32 Anzeige-Zellen nicht hinter „Nächste Tür“ (solange der Gang frei ist), bei 4 bis 18 Reihen Weg | dito |
| Wie weit sind die Regeln vom Orakel? | In 14 von 16 Zellen mit Tipp-Befolgern auf dem Orakel, in 2 um 1 Pp. darunter; die Lücke ist der Weg (Orakel 0 bis 1 Reihe, Regeln 4 bis 14) | `test_oracle_cells` |

## Ehrliche Grenzen

- **Kein Datenbezug.** Bündelung an Zugängen ist belegt (Bosina u. a., STRC 2015, Beobachtung an zwei Zürcher Bahnsteigen; Khomchuk u. a., arXiv 1808.06962, Wagen nahe Treppen stark belegt), ihre Stärke und die Kopplung an
  Sitzplätze sind gesetzt; in keiner der gelesenen Quellen ist die Sitzplatzverfügbarkeit Gegenstand.
- **Der Vorsprung des Tipps allein ist Annahme, nicht Ergebnis**: weil die Mitreisenden nicht weit laufen, bleibt der Hinterzug leer. Das Ergebnis ist der Kreuzungspunkt. Laufen alle weit und gibt es genug Plätze, verschwindet der Vorsprung.
- Der Herdeneffekt ist nicht neu (siehe oben), und die Messreihe zeigt, wie früh er einsetzt, nicht wie viele Fahrgäste den Tipp in Wirklichkeit kennen: φ und ψ sind Regler.
- **Anzeige:** Die Nutzer entscheiden gleichzeitig, steigen aber nacheinander ein; die Anzeige kennt die naiven Türgewichte, nicht den Anteil der anderen Nutzer.
- Eine frühere Fassung des „Blicks“ sah den Zustand im Moment des eigenen Einsteigens und lag zu gut; sie ist durch den Blick bei Ankunft ersetzt (Befund: Anzeige kippt, „Durchlaufen“ nicht).
- Nicht modelliert: gleichzeitiges Gehen, Türdurchsatz (alle Befolger an einer Tür), Gepäck und Fahrräder, Wagenreihung und Haltepunkt-Unsicherheit, Reservierungen, Klassen, Türöffnungszeit.

## Verifikation

122 Tests, Laufzeit etwa 4,5 Minuten (Windows, davon der Großteil AppTest-Läufe der Oberfläche; der Kern allein läuft in etwa einer Minute).

- **Kern:** Einheiten (`nearest_free`, `take_seat`, `alight`, `reseat_standing`, `board_naive`, Türbewertung) an der Mini-Instanz aus 2 Wagen × 2 Reihen × 1 Platz, von Hand gerechnet; SplitMix64-Referenzwert (`tests/test_units.py`).
- **Orakel** (`tests/test_oracle_sitzplatz.py`): Aufzählung aller 3072 Einstiegsfälle gegen eine unabhängig geschriebene Platzwahl; ein Wagen: erwartete Sitzende = E[min(N, S)] mit Poisson-N; Fokus-Fahrgast P(Platz) = E[min(1, S/(N+1))];
  drei Wagen mit Bündelung als Poisson-Ausdünnung.
- **Invarianten** je Halt (Plätze je Reihe, Sitzende gleich belegte Plätze, Stehzähler je Wagen) mit und ohne Blockade und mit Anzeige-Nutzern; gemeinsame Zufallszahlen über φ; Zweig-Tests je Strategie; Orakel nie schlechter als eine Regel (`tests/test_invariants.py`).
- **Messreihe:** Stichproben der Datei werden vom Kern exakt reproduziert (`tests/test_results.py`), jede README-Zahl in `tests/test_claims.py`.
- **Verdikte** an handgesetzten Werten (`tests/test_verdicts.py`), **Presets** und Permalink (`tests/test_presets.py`), **PDF** (`tests/test_pdf.py`).
- **Oberfläche:** AppTest-Rauchtest (jeder Button, jeder Regler am Minimum und Maximum), Footer-Test, Layout-Test (Schnellstart in der Seitenleiste, fester Kopf, aktives Preset hervorgehoben, jede Reglerwahl hebt die Markierung auf).
- **Mutationsprüfung** (`tools/mutation_check.py`, Mutanten in Kern, Auswertung, Presets und Messreihen-Auswertung): **35 von 35** Mutanten gefunden, einer davon über Zeitüberschreitung (die Mutation erzeugt eine Endlosschleife). Ausgenommen ein gleichwertiger Mutant: der Frühausstieg in `reseat_standing` ändert nur die Laufzeit. Im ersten Lauf überlebten fünf Mutanten der Anzeige-Erweiterung; je ein gezielter Test (Rückfall „durch den Zug laufen“, Zahl der Einsteigenden in der Türbewertung, Blick bei Ankunft statt live, Zwischenspeicher) ergänzt.

## Dateistruktur

| Datei | Zweck |
|---|---|
| `.github/workflows/tests.yml` | CI: Push, Pull Request, wöchentlicher Canary |
| `.gitignore` | venv, Caches, Streamlit-Secrets |
| `.streamlit/config.toml` | Streamlit-Einstellungen (keine Nutzungsstatistik) |
| `app.py` | Streamlit-App |
| `data/stz_results.json` | vorgerechnete Messreihe (576 + 64 + 24 + 16 + 32 Zellen) |
| `requirements-dev.txt` | Laufzeit plus pytest |
| `requirements.txt` | Laufzeit-Bibliotheken (ungepinnt) |
| `stz_constants.py` | Zuggeometrie, Annahmen, Regler-Grenzen, Farben, Presets |
| `stz_crowd.py` | Mitreisende: Start-Ziel-Paare, Türgewichte, Türwahl, Tipp- und Anzeige-Zuordnung |
| `stz_evaluation.py` | Einstellungen, Live-Rechnungen, Verdikte |
| `stz_layout.py` | Fester Kopf (Stylesheet) |
| `stz_pdf_export.py` | PDF-Steckbrief (fpdf2) |
| `stz_presets.py` | Permalink (Begrenzen, Einrasten), Presets (Schnellstart in der Seitenleiste), Zufalls-Seed-Button |
| `stz_results.py` | Laden und Auswerten der vorgerechneten Messreihe |
| `stz_rng.py` | ganzzahliger SplitMix64-Generator |
| `stz_runs.py` | gepaarter Strategievergleich, Orakel, Kurven, Kreuzungspunkt |
| `stz_strategies.py` | Strategien des Fokus-Fahrgasts |
| `stz_train.py` | Zugzustand und Einheiten: Platzsuche, Platznahme, Halt, Einsteigen, Türbewertung |
| `stz_visualization.py` | Plotly-Abbildungen (Achsen gesperrt) |
| `tools/` | `sweep_*.py` (Messreihe), `dump_sweep.py` (Datei bauen), `mutation_check.py`, `raw/` (Rohdaten der Sweeps) |
| `tests/` | Einheiten, Orakel, Invarianten, Messreihe, Claims, Verdikte, Presets, PDF, Layout, AppTest-Smoke-Test, AppTest der Optionsregler und Radios, Footer, Laufzeit-Importe |

## Bewusst nicht umgesetzt

- **Gleichzeitiges Gehen und Türdurchsatz:** Eine Tür, an der alle Befolger ankommen, würde zusätzlich verstopfen; im Modell steigen alle nacheinander ein.
- **Kalibrierung an echten Zügen:** Es gibt keine Daten zur Sitzplatzverfügbarkeit nach Wagen in den gelesenen Quellen; ohne sie bleibt jede Stärke der Bündelung eine Annahme.
- **Reservierungen und Intervallfärbung:** Sitzplatzzuweisung mit Reservierung ist ein anderes Modell (Betreiberseite, siehe `revenue-management-demo`).
- **„Weiterlaufen oder nehmen“ als optimales Stoppen:** Das wäre dasselbe Modell wie `routenresilienz-demo` in neuer Kulisse.
- **Anzeige, die den Anteil der Nutzer kennt:** Die Anzeige rechnet nur mit den naiven Türgewichten; eine, die ψ einrechnet, wäre ein eigenes Stück.

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Gebaut mit Streamlit, Plotly, pandas und fpdf2.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zum Thema: [Schienenverkehr optimieren](https://sebastianhanisch.net/schienenverkehr-optimierung.html).
