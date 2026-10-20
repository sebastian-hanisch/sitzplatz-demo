"""Sitzplatz im Zug ohne Reservierung – wohin am Bahnsteig, wenn alle dasselbe wollen? - interaktive Fall-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Siebter Baustein der Reihe Bahn/Schienenverkehr und der erste aus Sicht der Fahrgäste: Ein Zug mit freier Platzwahl, Mitreisende, die sich
an den Treppen des Bahnsteigs bündeln, und ein Fokus-Fahrgast, der eine Strategie wählt. Gemessen wird der Sitzanteil der Fahrt, und ab welchem
Anteil Mitwisser ein Tipp (oder eine Auslastungsanzeige) seinen Vorsprung verliert. Alle Verhaltensparameter sind Annahmen, keine Messungen.

Lauffähig mit: streamlit run app.py
"""

import time
from dataclasses import replace

import pandas as pd
import streamlit as st

import stz_constants as C
import stz_results as R
from stz_evaluation import (Settings, best_strategy, compare, pct, phi_points, psi_points, psi_crossing, train_view, verdict_phi, verdict_psi,
                            verdict_seat)
from stz_layout import dunkles_design, kopf_css
from stz_pdf_export import generate_pdf
from stz_presets import (
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    sidebar_presets,
    sync_query_params,
)
from stz_runs import phi_star
from stz_visualization import build_phi_curve, build_phi_map, build_psi_curve, build_strategies, build_train

st.set_page_config(page_title="Sitzplatz ohne Reservierung – Sebastian Hanisch", layout="wide")


@st.cache_data(show_spinner=False)
def _results():
    return R.load_results()


@st.cache_data(show_spinner=False)
def _compare(settings):
    t = time.perf_counter()
    return compare(settings), time.perf_counter() - t


@st.cache_data(show_spinner=False)
def _phi(settings):
    t = time.perf_counter()
    return phi_points(settings), time.perf_counter() - t


@st.cache_data(show_spinner=False)
def _psi(settings):
    t = time.perf_counter()
    return psi_points(settings), time.perf_counter() - t


@st.cache_data(show_spinner=False)
def _view(settings):
    return train_view(settings)


@st.cache_data(show_spinner=False)
def _oracle(settings):
    return compare(settings, n=C.ORACLE_RUNS, oracle=True)


def _block_label(b):
    return "aus" if b == 0 else f"ab {b} Stehenden"


# Fester Kopf: nur der Titel bleibt beim Scrollen oben (Stylesheet in stz_layout.py).
st.html(kopf_css(dunkles_design()))
with st.container(key="kopf"):
    st.title("💺 Sitzplatz im Zug ohne Reservierung – wohin am Bahnsteig, wenn alle dasselbe wollen?")
st.markdown(
    """
Im Zug ohne Platzreservierung gilt der Tipp **„geh ans Zugende“**: Die Wagen an den **Treppen** des Bahnsteigs sind voll, hinten ist es leer. Die Demo
fragt, **wie lange dieser Tipp trägt**, wenn ihn immer mehr Mitreisende kennen, und ob eine **Auslastungsanzeige** besser dasteht. Sie vergleicht Strategien für einen
Fahrgast (nächste Tür, Zugende, durchlaufen, stehen bleiben, Anzeige) auf einem Zug mit 320 Plätzen, live auf gleichen Zugverläufen und vorgerechnet über
Hunderte von Annahme-Zellen. **Alles hier ist Modell mit gesetzten Annahmen, keine Messung im Zug.**

Weiter unten: die **Kernfrage** (ab welchem Anteil Mitwisser kippt der Tipp?), zwei Experimente und die Expander **🔧 Wie wir das erreichen – vollständiger Methodenvergleich**
und **📐 Mathematische Formulierung**.
"""
)

# erklaerseite:einfach:start (erzeugt von tools/set_demo_explainer.py (Website-Repo) aus tools/content/explainers/sitzplatz-im-zug-erklaert.json, nicht von Hand ändern)
with st.expander("💬 In einfachen Worten"):
    st.markdown(
        """
Stellen Sie sich einen Zug ohne Platzreservierung vor. Viele steigen bevorzugt an den Türen ein, die dem Zugang des Bahnsteigs am nächsten liegen. Dort sind die Wagen voll, während hinten Plätze frei bleiben. Daher der Tipp „geh ans Zugende“. Kennen ihn aber viele, wird es auch dort voll: ein **Herdeneffekt**. Die Demo fragt, ab welchem Anteil Mitwissender der Tipp seinen Vorsprung verliert und ob eine Auslastungsanzeige besser dasteht. Dazu vergleicht sie mehrere Strategien für einen Fahrgast auf denselben Zugverläufen. Alle Verhaltensannahmen sind gesetzt und nicht im Zug gemessen: Die Aussagen gelten im Modell.

[Ausführlich und verständlich erklärt, mit Fachteil](https://sebastianhanisch.net/sitzplatz-im-zug-erklaert.html)
        """
    )
# erklaerseite:einfach:end
st.caption(
    "Erster Baustein der Reihe [Bahn/Schienenverkehr](https://sebastianhanisch.net/schienenverkehr-optimierung.html) aus Sicht der Fahrgäste. Der Herdeneffekt "
    "(„alle springen zum leersten Tor“) steht schon in [nash-demo](https://sebastianhanisch-nash-demo.streamlit.app/), dort mit Wartezeit statt Platzschwelle."
)
st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    sidebar_presets()  # Schnellstart oben, das aktive Preset ist hervorgehoben
    st.header("⚙️ Einstellungen")
    st.markdown("**Zug und Mitreisende**")
    rho = st.slider("Spitzenlast (% der Sitzplätze)", *bounds("rho_slider"), step=10, key="rho_slider",
                    help="Fahrgäste am stärksten Querschnitt der Linie in Prozent der 320 Sitzplätze. Über 100 % gibt es mehr Fahrgäste als Plätze.")
    stair = st.select_slider("Treppen-Bündelung", options=C.STAIR_OPTIONS, key="stair_select",
                             help="Wie stark sich die Mitreisenden an den Türen am Zugang des Bahnsteigs drängen (Gewicht der Tür dort = 1 + Wert). 0 = gleichmäßig.")
    reach = st.select_slider("Reichweite der Mitreisenden (Reihen)", options=C.REACH_OPTIONS, key="reach_select",
                             help="Wie weit ein Mitreisender nach einem freien Platz sucht (10 Reihen = 1 Wagen); 80 = der ganze Zug.")
    block = st.select_slider("Gang blockiert", options=C.BLOCK_OPTIONS, key="block_select", format_func=_block_label,
                             help="Ein Wagen mit mindestens so vielen Stehenden ist nicht passierbar. Wirkt nur auf alle, die durch einen vollen Wagen laufen wollen.")
    stop = st.slider("Einstiegshalt des Fahrgasts", *bounds("stop_slider"), key="stop_slider",
                     help="An welchem der 10 Halte der Linie Sie einsteigen (Fahrt: 3 Halte). Frühe Halte: der Zug ist noch leerer.")
    st.markdown("**Wer kennt den Tipp, wer sieht die Anzeige?**")
    phi = st.slider("Anteil, der dem Tipp folgt (%)", *bounds("phi_slider"), step=10, key="phi_slider",
                    help="Anteil der Mitreisenden, die dem Tipp „Zugende“ folgen. Die Kurve der Kernfrage läuft über diesen Anteil; hier steht der Wert für die Zugdarstellung und die anderen Abschnitte.")
    advice = st.radio("Tipp-Art", C.ADVICE_OPTIONS, key="advice_radio", format_func=C.ADVICE_LABELS.get, disabled=phi == 0,
                      help="Wohin die Tipp-Befolger gehen. Erst ab einem Anteil über 0 wirksam; bei 0 ist der Regler abgeschaltet.")
    psi = st.slider("Anteil mit Anzeige (%)", *bounds("psi_slider"), step=10, key="psi_slider",
                    help="Anteil der Mitreisenden, die bei Einfahrt des Zuges die Auslastung sehen und danach ihre Tür wählen.")
    mode = st.radio("Anzeige-Modus", C.MODE_OPTIONS, key="mode_radio", format_func=C.MODE_LABELS.get, disabled=psi == 0,
                    help="Alle Anzeige-Nutzer gehen zur besten Tür, oder sie würfeln im Verhältnis der Bewertung (die übliche Gegenmaßnahme gegen den Herdeneffekt). Erst ab Anteil über 0 wirksam.")
    st.markdown("**Zufall**")
    seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), key="seed_input", step=1,
                           help="Bestimmt die 40 Zugverläufe der Live-Rechnung (gleiche Verläufe für alle Strategien).")
    st.button("🎲 Neue Zugverläufe würfeln", width="stretch", on_click=randomize_seed)

settings = Settings(rho=int(rho), stair=int(stair), reach=int(reach), stop=int(stop), phi=int(phi), psi=int(psi), advice=advice, mode=mode,
                    block=int(block), seed=int(seed))
sync_query_params({"rho_slider": settings.rho, "stair_select": settings.stair, "reach_select": settings.reach, "stop_slider": settings.stop,
                   "phi_slider": settings.phi, "psi_slider": settings.psi, "advice_radio": settings.advice, "mode_radio": settings.mode,
                   "block_select": settings.block, "seed_input": settings.seed})
res = _results()

# --- Ergebnis ------------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Wohin am Bahnsteig? Sitzanteil je Strategie")
with st.spinner(f"Rechne {C.LIVE_RUNS} Zugverläufe mit fünf Strategien …"):
    rows, secs = _compare(settings)
view = _view(settings)
ref = rows["naechste"]["sitz"]
cols = st.columns(4)
for col, k in zip(cols, ("naechste", "ende", "durchlaufen", "blick_ankunft")):
    # Delta immer als „mein Wert minus Referenz“; höher ist besser, also ohne Umkehr der Farbe (DEMO-PLAYBOOK §2).
    col.metric(C.STRATEGY_LABELS[k], pct(rows[k]["sitz"]),
               delta=("Referenz" if k == "naechste" else f"{100 * (rows[k]['sitz'] - ref):+.0f} Pp. gegen Nächste Tür"),
               delta_color="off" if k == "naechste" else "normal", help=C.STRATEGY_EXPLAIN[k])
st.caption(f"Sitzanteil = Anteil der 3 Fahrtabschnitte, in denen Sie sitzen. Mittel über {C.LIVE_RUNS} gleiche Zugverläufe je Strategie (Fehlerbalken = Standardfehler), "
           f"Rechenzeit {secs:.1f} s beim ersten Aufruf, danach aus dem Zwischenspeicher.")
st.plotly_chart(build_strategies(rows), width="stretch", key="strategies_chart")
kind, text = verdict_seat(rows)
getattr(st, kind)(text)

st.markdown("**Der Zug bei Einfahrt an Halt " + str(settings.stop) + "** (ein Beispiel-Lauf; Marker = gewählte Tür der Strategie in diesem Lauf)")
st.plotly_chart(build_train(view), width="stretch", key="train_chart")
st.caption(f"Oben: Anteil der Mitreisenden je Tür (Bündelung, Anzeige-Nutzer und Tipp-Befolger sind in diesem Bild nicht eingerechnet). Mitte: belegte Plätze je Reihe, 10 Reihen = 1 Wagen. "
           f"Stehende je Wagen: {', '.join(str(x) for x in view['standing'])}. Einsteigende an diesem Halt: {view['boarders']}.")

verdicts_for_pdf = [text]
sets_for_pdf = {
    "Spitzenlast": f"{settings.rho} % der Sitzplätze", "Treppen-Bündelung": f"a = {settings.stair}", "Reichweite der Mitreisenden": f"{settings.reach} Reihen",
    "Gang blockiert": _block_label(settings.block), "Einstiegshalt": f"Halt {settings.stop} (Fahrt 3 Halte)", "Anteil Tipp-Befolger": f"{settings.phi} % ({C.ADVICE_LABELS[settings.advice]})",
    "Anteil Anzeige-Nutzer": f"{settings.psi} % ({C.MODE_LABELS[settings.mode]})", "Zufalls-Seed": settings.seed,
}

# --- Kernfrage -----------------------------------------------------------------------------------------------------------------------------

st.markdown("---")
st.markdown("## ❓ Kernfrage: Ab welchem Anteil Mitwisser verliert der Tipp „ans Zugende“ seinen Vorsprung?")
with st.spinner(f"Rechne {len(C.CURVE_PHIS)} Anteile × {C.LIVE_RUNS} Läufe …"):
    points, phi_secs = _phi(replace(settings, phi=0))
star = phi_star(points)
kind, text = verdict_phi(points)
getattr(st, kind)(text)
verdicts_for_pdf.append(text)
st.plotly_chart(build_phi_curve(points, star), width="stretch", key="phi_curve")
st.caption(f"Live: {C.LIVE_RUNS} gleiche Zugverläufe je Punkt (gemeinsame Zufallszahlen über alle Anteile), Rechenzeit {phi_secs:.1f} s beim ersten Aufruf. "
           f"Die Kurve läuft über den Anteil der Befolger (der Regler „Anteil, der dem Tipp folgt“ gilt hier nicht); alle übrigen Einstellungen gelten, auch der Anteil mit Anzeige ({settings.psi} %).")

s_end, s_wide = R.star_summary(res, "ende"), R.star_summary(res, "verteilt")
st.markdown(
    f"**Messreihe über {s_end['cells']} Zellen je Tipp-Art** (Bündelung × Reichweite × Spitzenlast × Einstiegshalt × Gangblockade, je {res['meta']['runs_phi']} Läufe): "
    f"In {s_end['with_star']} Zellen hat der Tipp allein einen Vorsprung und kippt dann bei einem Anteil von **{100 * s_end['min']:.0f} bis {100 * s_end['max']:.0f} %** "
    f"(Median {100 * s_end['median']:.0f} %); verteilen sich die Befolger über die hintere Wagenhälfte, sind es {100 * s_wide['min']:.0f} bis {100 * s_wide['max']:.0f} % "
    f"(Median {100 * s_wide['median']:.0f} %). In {s_end['no_advantage']} Zellen hat der Tipp von Anfang an keinen Vorsprung."
)
st.plotly_chart(build_phi_map(R.phi_map(res, "ende")), width="stretch", key="phi_map")
st.caption("Median des Kreuzungspunkts (Tipp „alle ans Zugende“), gepoolt über Reichweite, Einstiegshalt und Gangblockade. „kein Vorteil“: In allen diesen Zellen "
           "liegt der Tipp schon ohne Mitwisser nicht vorn. Ohne Bündelung (a = 0) gibt es nie einen Vorsprung; mit Bündelung und Spitzenlast ab 100 % immer.")

# --- Experiment 1: Anzeige -----------------------------------------------------------------------------------------------------------------

st.markdown("### 🔬 Experiment: Was, wenn viele die Auslastungsanzeige nutzen?")
st.markdown(
    "Eine Anzeige bei Einfahrt zeigt, wo Plätze frei sind. Die Literatur schlägt sie vor, damit sich Wartende gleichmäßiger verteilen. "
    "Hier sehen **alle Anzeige-Nutzer gleichzeitig denselben Zustand**: Gehen sie alle zur besten Tür, ist sie beim Einsteigen voll."
)
with st.spinner(f"Rechne {len(C.CURVE_PSIS)} Anteile × {C.LIVE_RUNS} Läufe …"):
    psi_rows, psi_secs = _psi(replace(settings, psi=0))
kind, text = verdict_psi(psi_rows)
getattr(st, kind)(text)
verdicts_for_pdf.append(text)
st.plotly_chart(build_psi_curve(psi_rows, psi_crossing(psi_rows)), width="stretch", key="psi_curve")
ps_best = R.psi_star(R.psi_cell(res, 1.2, 0.0, "bester"))
ps_wtd = R.psi_star(R.psi_cell(res, 1.2, 0.0, "gewichtet"))
st.caption(f"Live mit Anzeige-Modus „{C.MODE_LABELS[settings.mode]}“ und Tipp-Anteil {settings.phi} %, {C.LIVE_RUNS} Läufe je Punkt, Rechenzeit {psi_secs:.1f} s beim ersten Aufruf. "
           f"Vorgerechnet (Spitzenlast 120 %, ohne Tipp-Befolger, je {res['meta']['runs_psi']} Läufe): Kreuzung bei etwa {100 * ps_best:.0f} % Nutzern, wenn alle zur besten Tür gehen; "
           "mit zufälliger Wahl im Verhältnis der Bewertung hält der Vorsprung länger, ist ab etwa 40 % aber nicht mehr vom „Nächste Tür“ zu unterscheiden. "
           "Bei 100 % Spitzenlast (genug Plätze) tritt der Effekt nicht auf. „Durchlaufen“ liegt bei Spitzenlast 120 % in allen 32 vorgerechneten Zellen nicht hinter „Nächste Tür“.")

# --- Experiment 2: Wann hilft der Tipp gar nicht --------------------------------------------------------------------------------------------

st.markdown("### 🔬 Experiment: Wann hilft der Tipp gar nicht?")
rb = R.reach_block_rows(res)
tab = []
for rho_v in (1.0, 1.2):
    for reach_v in (20, 40, 60, 80):
        cell = next(c for c in rb if c["rho"] == rho_v and c["reach"] == reach_v and c["block"] is None)
        sstar = R.cell_star(cell)
        tab.append({"Spitzenlast": f"{round(100 * rho_v)} %", "Reichweite der Mitreisenden": f"{reach_v} Reihen", "Nächste Tür": pct(cell["naechste"]),
                    "Zugende": pct(cell["ende"]),
                    "Kreuzungspunkt": ("kein Vorteil" if sstar == R.NO_ADVANTAGE else "–" if sstar is None else pct(sstar))})
st.dataframe(pd.DataFrame(tab), width="stretch", hide_index=True)
st.caption("Vorgerechnet (Bündelung a = 4, Einstiegshalt 3, ohne Gangblockade, je 100 Läufe), ohne Mitwisser. Laufen die Mitreisenden den ganzen Zug ab "
           "und gibt es genug Plätze, ist auch „Nächste Tür“ fast immer erfolgreich und der Tipp hat nichts zu gewinnen. Der Vorsprung ist eine Folge der Annahme, dass die Mitreisenden nicht weit laufen.")

st.markdown("---")

# --- Methodenvergleich ---------------------------------------------------------------------------------------------------------------------

with st.expander("🔧 Wie wir das erreichen – vollständiger Methodenvergleich"):
    tab_rules, tab_oracle = st.tabs(["Strategien im Vergleich", "🧮 Orakel unter den Regeln"])
    with tab_rules:
        st.markdown("**Was jede Strategie tut** (alle wählen eine Tür und suchen dann einen Platz; Reichweite wie oben eingestellt, falls nicht anders genannt):")
        st.dataframe(pd.DataFrame([{"Strategie": C.STRATEGY_LABELS[k], "Regel": C.STRATEGY_EXPLAIN[k],
                                    "Sitzanteil": pct(rows[k]["sitz"]), "Platz beim Einsteigen": pct(rows[k]["sofort"]),
                                    "Weg (Reihen)": f"{rows[k]['weg']:.0f}"} for k in C.APP_STRATEGIES]), width="stretch", hide_index=True)
        st.caption(f"Gewählt wird im Beispiel nach dem höchsten Sitzanteil: {C.STRATEGY_LABELS[best_strategy(rows)]}. „Platz beim Einsteigen“ = Anteil der Läufe, in denen schon beim Einsteigen ein Sitzplatz frei war.")
        tbl = R.table_cells(res)
        st.markdown(f"**Vorgerechnet** ({len(tbl)} Zellen: Spitzenlast × Einstiegshalt × Gangblockade, Bündelung a = 4, je {res['meta']['runs_table']} Läufe, ohne Mitwisser): "
                    f"„Zugende“, „Anzeige“ und das Orakel haben in allen {len(tbl)} Zellen {pct(min(min(c['res'][k]['sitz'] for k in ('ende', 'blick_ankunft', 'orakel')) for c in tbl))} und mehr. "
                    "Das ist die Annahme des leeren Hinterzugs, kein Ergebnis; der Unterschied liegt im Weg und, sobald Mitwisser dazukommen, im Sitzanteil.")
    with tab_oracle:
        # Der Tab ist selbstständig: eigener Button, Spinner und Ergebnis, gegen das aktuelle Szenario geprüft (DEMO-PLAYBOOK §2).
        st.markdown("**Orakel unter den Regeln:** probiert für jeden Lauf alle 16 Türen mit „sofort suchen“, „durchlaufen“ und „stehen bleiben“ und nimmt den besten Ausgang "
                    "(kennt also die Zukunft des Laufs). Es zeigt, wie viel die besten Regeln liegen lassen.")
        og = R.oracle_gap(res)
        st.caption(f"Vorgerechnet über {og['cells']} Zellen mit Tipp-Befolgern (20 und 40 %): Die beste Regel liegt in {og['on_oracle']} Zellen auf dem Orakel, "
                   f"höchstens {100 * og['max_gap']:.0f} Prozentpunkt darunter. Die Lücke ist der Weg: Das Orakel bleibt an der richtigen Tür stehen (0 bis 1 Reihe), die Regeln laufen 4 bis 14 Reihen.")
        if st.button(f"Orakel für diese Einstellung rechnen ({C.ORACLE_RUNS} Läufe)", key="oracle_start"):
            st.session_state["oracle_done"] = settings
        if st.session_state.get("oracle_done") == settings:
            with st.spinner(f"Probiere alle Türen und Modi in {C.ORACLE_RUNS} Läufen (etwa 10 Sekunden) …"):
                o_rows = _oracle(settings)
            st.plotly_chart(build_strategies(o_rows, with_oracle=True), width="stretch", key="oracle_chart")
            st.caption(f"Nur {C.ORACLE_RUNS} Läufe (jeder probiert 48 Ausgänge): die Zahlen weichen von denen oben ab und streuen um einige Prozentpunkte; die Aussage steht in der vorgerechneten Zeile darüber.")
            st.metric("Orakel gegen beste Regel", pct(o_rows["orakel"]["sitz"]),
                      delta=f"{100 * (o_rows['orakel']['sitz'] - max(o_rows[k]['sitz'] for k in C.APP_STRATEGIES)):+.0f} Pp. gegen die beste Regel", delta_color="off")

with st.expander("📐 Mathematische Formulierung"):
    # erklaerseite:lesehilfe:start (erzeugt von tools/set_demo_explainer.py (Website-Repo) aus tools/content/explainers/sitzplatz-im-zug-erklaert.json, nicht von Hand ändern)
    st.markdown(
        r"""
**Lesehilfe.** Gegeben sind der Zug mit seinen Plätzen und Türen, die Bündelung der Mitreisenden an den Treppen und die Anteile, die dem Tipp folgen oder die Anzeige nutzen. Gesucht ist der Sitzanteil des Fahrgasts je Strategie und der Anteil $\varphi^{*}$, ab dem der Tipp „Zugende“ nicht mehr vor „Nächste Tür“ liegt.

| Symbol | Bedeutung |
|---|---|
| $d$, $d_0$ | Tür, Tür am Zugang des Bahnsteigs |
| $a$ | Stärke der Bündelung an den Treppen |
| $\sigma$ | Streuung der Bündelung (in Reihen) |
| $w_d$ | Gewicht der Tür $d$ bei der Türwahl |
| $N$, $S_c$ | Zahl der Mitreisenden, die in einen Wagen drängen, und dessen freie Plätze |
| $\varphi$ | Anteil der Mitreisenden, die dem Tipp folgen |
| $\bar x_{\text{Ende}}$, $\bar x_{\text{nah}}$ | mittlerer Sitzanteil bei „Zugende“ bzw. „Nächste Tür“ |
| $\varphi^{*}$ | Kreuzungspunkt |
| $F_d$, $n$, $q_d$ | freie Plätze im Umkreis der Tür, Zahl der Einsteigenden, naiver Türanteil im Umkreis |

[Schritt für Schritt erklärt, mit Herleitung und Literatur](https://sebastianhanisch.net/sitzplatz-im-zug-erklaert.html#fachleute)
        """
    )
    # erklaerseite:lesehilfe:end
    st.markdown("**Mitreisende.** Jedes Start-Ziel-Paar der Linie mit $M$ Halten bringt eine Poisson-verteilte Zahl von Fahrgästen; die Rate ist so gewählt, "
                "dass der stärkste Querschnitt auf die Spitzenlast $\\rho$ der $S$ Sitzplätze kommt:")
    st.markdown("$$\\lambda = \\frac{\\rho\\, S}{\\lfloor M/2\\rfloor\\,\\lceil M/2\\rceil}$$")
    st.markdown("**Türwahl der Naiven.** Die Tür $d$ bekommt das Gewicht (Bündelung $a$ um den Zugang $d_0$ mit Streuung $\\sigma$):")
    st.markdown("$$w_d = 1 + a\\,e^{-\\frac{(d-d_0)^2}{2\\sigma^2}}$$")
    st.markdown("und wird mit der Wahrscheinlichkeit gewählt:")
    st.markdown("$$P(d) = \\frac{w_d}{\\sum_{d'} w_{d'}}$$")
    st.markdown("**Platzwahl.** Von der Tür an Reihe $p$ wird die nächste Reihe mit freiem Platz im Umkreis $R$ genommen, sonst steht man:")
    st.markdown("$$r^{*} = \\arg\\min_{r:\\ f_r>0,\\ |r-p|\\le R} |r-p|$$")
    st.markdown("**Kapazitätsschwelle.** Ohne Weiterlaufen hängt der Platz nur von der Einstiegsreihenfolge ab: Unter $N$ Mitreisenden, die in einen Wagen mit $S_c$ freien Plätzen drängen, "
                "sitzt der Fahrgast mit der Wahrscheinlichkeit:")
    st.markdown("$$P(\\text{Platz}) = \\mathbb{E}\\left[\\min\\left(1,\\ \\frac{S_c}{N+1}\\right)\\right]$$")
    st.markdown("(geprüft gegen die Simulation in `tests/test_oracle_sitzplatz.py`). **Sitzanteil** der Fahrt über $T$ Abschnitte:")
    st.markdown("$$x = \\frac{\\#\\{\\text{Abschnitte mit Sitzplatz}\\}}{T}$$")
    st.markdown("**Kreuzungspunkt.** Mit $\\bar x_{\\text{Ende}}(\\varphi)$ und $\\bar x_{\\text{nah}}(\\varphi)$ als Mittel über die gleichen Zugverläufe, wenn der Anteil $\\varphi$ dem Tipp folgt:")
    st.markdown("$$\\varphi^{*} = \\min\\{\\varphi:\\ \\bar x_{\\text{Ende}}(\\varphi) \\le \\bar x_{\\text{nah}}(\\varphi)\\}$$")
    st.markdown("(linear zwischen den Rasterpunkten interpoliert; „kein Vorteil“, wenn der Vorsprung bei $\\varphi=0$ höchstens 0,02 beträgt.) "
                "**Anzeige.** Bewertung je Tür bei Einfahrt mit freien Plätzen $F_d$ im Umkreis, $n$ Einsteigenden und dem naiven Türanteil $q_d$ im Umkreis:")
    st.markdown("$$\\text{Wert}_d = \\frac{F_d}{1 + n\\, q_d}$$")

with st.expander("📋 Annahmen: wer setzt was an"):
    st.dataframe(pd.DataFrame([
        {"Annahme": "Zug", "Wert": "8 Wagen × 10 Reihen × 4 Plätze = 320 Plätze, 16 Türen an den Wagenenden", "Wer setzt an": "Demo-Autor", "Beleg": "gesetzt"},
        {"Annahme": "Linie und Nachfrage", "Wert": "10 Halte, jedes Start-Ziel-Paar Poisson, Spitzenlast per Regler", "Wer setzt an": "Demo-Autor / Regler", "Beleg": "gesetzt"},
        {"Annahme": "Bündelung an Zugängen", "Wert": "Gewicht 1 + a, Zugang bei Reihe 25, Streuung 15 Reihen", "Wer setzt an": "Regler (a)", "Beleg": "qualitativ belegt (Bosina u. a. 2015; Khomchuk u. a. 2018), Stärke gesetzt"},
        {"Annahme": "Platzwahl der Mitreisenden", "Wert": "nächste freie Reihe in Reichweite, sonst Stehplatz an der Tür", "Wer setzt an": "Regler (Reichweite)", "Beleg": "gesetzt; Kopplung an Sitzplätze in keiner gefundenen Quelle"},
        {"Annahme": "Stehende rücken nach", "Wert": "Reichweite 15 Reihen zu einem frei gewordenen Platz", "Wer setzt an": "Demo-Autor", "Beleg": "gesetzt"},
        {"Annahme": "Gangblockade", "Wert": "Wagen mit ≥ n Stehenden nicht passierbar", "Wer setzt an": "Regler", "Beleg": "gesetzt"},
        {"Annahme": "Einstiegsreihenfolge", "Wert": "zufällig, nacheinander", "Wer setzt an": "Demo-Autor", "Beleg": "gesetzt"},
        {"Annahme": "Tipp-Befolger", "Wert": "Anteil φ geht an die Türen des letzten Wagens (oder verteilt über die hintere Hälfte)", "Wer setzt an": "Regler", "Beleg": "gesetzt"},
        {"Annahme": "Anzeige", "Wert": "Anteil ψ sieht den Zustand bei Einfahrt; die Anzeige kennt die naiven Türgewichte, nicht ψ", "Wer setzt an": "Regler", "Beleg": "gesetzt"},
        {"Annahme": "Fahrt des Fokus-Fahrgasts", "Wert": "3 Halte, Sitzanteil über die 3 Abschnitte", "Wer setzt an": "Demo-Autor", "Beleg": "gesetzt"},
    ]), width="stretch", hide_index=True)

with st.expander("🚧 Wo die Annahmen enden"):
    st.markdown(
        """
- **Kein Datenbezug.** Die Bündelung an Zugängen ist in der Literatur beschrieben (Wagen nahe Treppen sind voller), ihre Stärke und die Kopplung an Sitzplätze sind hier gesetzt.
  Die Aussage lautet „im Modell, unter diesen Annahmen“, nie „im Zug ist es so“.
- **Der Vorsprung des Tipps allein ist Annahme, nicht Ergebnis:** Weil die Mitreisenden nicht weit laufen, bleibt der Hinterzug leer. Das Ergebnis ist der Kreuzungspunkt und der Verlauf über den Anteil der Mitwisser.
  Laufen alle den ganzen Zug ab und gibt es genug Plätze, verschwindet der Vorsprung (siehe das Experiment oben).
- **Nicht modelliert:** gleichzeitiges Gehen, Türdurchsatz (alle Befolger an einer Tür), Gepäck und Fahrräder, Wagenreihung und Haltepunkt-Unsicherheit, Reservierungen, Klassen, Türöffnungszeit.
- **Anzeige:** Die Nutzer entscheiden gleichzeitig, steigen aber nacheinander ein; die Anzeige kennt den Anteil der anderen Nutzer nicht.
- Der Herdeneffekt selbst ist nicht neu (siehe [nash-demo](https://sebastianhanisch-nash-demo.streamlit.app/)); neu sind die Platzschwelle, der Anteil Mitwisser als Regler und die Zeitachse mit Nachrücken.
"""
    )

st.download_button("📄 Steckbrief dieser Einstellung als PDF herunterladen", data=generate_pdf(sets_for_pdf, rows, verdicts_for_pdf, C.LIVE_RUNS),
                   file_name="sitzplatz-steckbrief.pdf", mime="application/pdf", key="pdf_download")

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zum Thema: [Schienenverkehr optimieren](https://sebastianhanisch.net/schienenverkehr-optimierung.html)."
)
