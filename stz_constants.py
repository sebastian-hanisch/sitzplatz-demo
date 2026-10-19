"""Zuggeometrie, Annahmen, Regler-Grenzen, Farben und Presets. Alle Verhaltensparameter sind Annahmen (siehe README), keine Messungen."""
from dataclasses import dataclass, field


@dataclass(frozen=True, kw_only=True)
class Layout:
    cars: int = 8      # Wagen
    rows: int = 10     # Sitzreihen je Wagen
    seats: int = 4     # Plätze je Reihe

    @property
    def n_rows(self):
        return self.cars * self.rows

    @property
    def n_seats(self):
        return self.n_rows * self.seats

    @property
    def doors(self):
        """Türen an beiden Wagenenden (Reihenindex der ersten und letzten Reihe je Wagen), aufsteigend, ohne Doppelte."""
        return tuple(sorted({c * self.rows for c in range(self.cars)} | {c * self.rows + self.rows - 1 for c in range(self.cars)}))

    def car_of(self, row):
        return row // self.rows


@dataclass(frozen=True, kw_only=True)
class Params:
    layout: Layout = field(default_factory=Layout)
    stops: int = 10              # Halte der Linie
    trip: int = 3                # Fahrstrecke des Fokus-Fahrgasts in Halten
    rho: float = 0.9             # Spitzenlast / Sitzplätze
    stair_row: float = 25.0      # Zugang am Bahnsteig (Reihenindex)
    stair_sigma: float = 15.0    # Streuung der Bündelung (Reihen)
    stair_a: float = 4.0         # Stärke der Bündelung (Tür am Zugang hat Gewicht 1 + a)
    phi: float = 0.0             # Anteil der Mitreisenden, die dem Tipp folgen
    advice: str = "ende"         # "ende" | "verteilt"
    reach_naive: int = 20        # Reichweite beim Platzsuchen (Reihen)
    reach_stand: int = 15        # Reichweite eines Stehenden zu einem frei gewordenen Platz
    block: int | None = None     # Gangblockade: ein Wagen mit >= block Stehenden ist nicht passierbar (None = aus)
    psi: float = 0.0             # Anteil der Mitreisenden mit Blick auf die einfahrende Garnitur (Auslastungsanzeige)
    blick_mode: str = "bester"   # "bester": alle Anzeige-Nutzer nehmen dieselbe beste Tür | "gewichtet": Tür zufällig im Verhältnis der Bewertung


STRATEGIES = ("naechste", "ende", "durchlaufen", "stehen", "blick")
APP_STRATEGIES = ("naechste", "ende", "durchlaufen", "stehen", "blick_ankunft")
STRATEGY_LABELS = {
    "naechste": "Nächste Tür",
    "ende": "Zugende (Tipp)",
    "durchlaufen": "Durchlaufen",
    "stehen": "Stehen bleiben",
    "blick_ankunft": "Anzeige (Blick bei Ankunft)",
    "blick": "Blick live",
    "orakel": "Orakel unter den Regeln",
}
STRATEGY_EXPLAIN = {
    "naechste": "Wie die Mitreisenden: Tür mit Treppen-Gewicht, nächster freier Platz in Reichweite, sonst stehen.",
    "ende": "Eine der beiden Türen des letzten Wagens, dann nächster freier Platz in Reichweite. Der bekannte Tipp.",
    "durchlaufen": "Wie „Nächste Tür“, aber danach durch den ganzen Zug zum nächsten freien Platz (die Gangblockade kann den Weg versperren).",
    "stehen": "Nächste Tür, auf der Plattform stehen bleiben und an jedem Halt einen frei gewordenen Platz in Reichweite nehmen.",
    "blick_ankunft": "Auslastungsanzeige bei Einfahrt des Zuges: Tür mit dem besten Verhältnis freie Plätze / erwartete Mitbewerber, sonst durchlaufen.",
}

# --- Regler (ganzzahlig; Anteile in Prozent, Last in Prozent der Sitzplätze) ---------------------------------------------------------------
RHO_MIN, RHO_MAX, DEFAULT_RHO = 60, 140, 120
PHI_MIN, PHI_MAX, DEFAULT_PHI = 0, 80, 0
PSI_MIN, PSI_MAX, DEFAULT_PSI = 0, 100, 0
STOP_MIN, STOP_MAX, DEFAULT_STOP = 2, 5, 3
SEED_MAX, DEFAULT_SEED = 999999, 35
STAIR_OPTIONS = (0, 2, 4, 8)
DEFAULT_STAIR = 4
REACH_OPTIONS = (10, 20, 40, 80)
DEFAULT_REACH = 20
BLOCK_OPTIONS = (0, 8, 4)                   # 0 = aus
DEFAULT_BLOCK = 8
ADVICE_OPTIONS = ("ende", "verteilt")
ADVICE_LABELS = {"ende": "Alle an die Türen des letzten Wagens", "verteilt": "Gleichmäßig über die hintere Wagenhälfte"}
MODE_OPTIONS = ("bester", "gewichtet")
MODE_LABELS = {"bester": "Alle zur besten Tür", "gewichtet": "Zufällig im Verhältnis der Bewertung"}

# --- Läufe ---------------------------------------------------------------------------------------------------------------------------------
ORACLE_RUNS = 10                            # Läufe der Live-Orakel-Rechnung (48 Ausgänge je Lauf)
LIVE_RUNS = 40                              # Läufe je Punkt der Live-Rechnung (gepaarter Vergleich, gleiche Zufallszahlen über alle Strategien)
CURVE_PHIS = (0.0, 0.1, 0.2, 0.3, 0.4, 0.6)
CURVE_PSIS = (0.0, 0.2, 0.4, 0.6, 1.0)
SEED_BASE = 1000                            # Läufe nutzen die Seeds SEED_BASE + i; der Regler „Zufalls-Seed“ verschiebt den Start
RESULTS_FILE = "data/stz_results.json"
SWEEP_RUNS = 100                            # Läufe je Punkt der vorgerechneten Messreihe
NOISE_NOTE = 0.02                           # Unterschiede unter 0,02 Sitzanteil gelten als gleich (Vorsprung bei phi = 0)

COLOR_FREE = "#e8e8e8"
COLOR_TAKEN = "#4c78a8"
COLOR_STAIR = "#d98a2b"
COLOR_DOOR = "#2F6B65"
STRATEGY_COLORS = {"naechste": "#9a9a9a", "ende": "#d98a2b", "durchlaufen": "#4c78a8", "stehen": "#b8b8b8", "blick_ankunft": "#2F6B65"}

PRESETS = {
    "Pendlerzug voll (Voreinstellung)": {"rho": 120, "stair": 4, "reach": 20, "stop": 3, "phi": 0, "psi": 0, "advice": "ende", "mode": "bester", "block": 8, "seed": DEFAULT_SEED},
    "Halbleerer Zug": {"rho": 80, "stair": 4, "reach": 20, "stop": 3, "phi": 0, "psi": 0, "advice": "ende", "mode": "bester", "block": 8, "seed": DEFAULT_SEED},
    "Starke Treppe": {"rho": 120, "stair": 8, "reach": 20, "stop": 3, "phi": 0, "psi": 0, "advice": "ende", "mode": "bester", "block": 8, "seed": DEFAULT_SEED},
    "Ohne Bündelung": {"rho": 120, "stair": 0, "reach": 20, "stop": 3, "phi": 0, "psi": 0, "advice": "ende", "mode": "bester", "block": 8, "seed": DEFAULT_SEED},
    "Jeder Dritte kennt den Tipp": {"rho": 120, "stair": 4, "reach": 20, "stop": 3, "phi": 30, "psi": 0, "advice": "ende", "mode": "bester", "block": 8, "seed": DEFAULT_SEED},
    "Breiter Tipp": {"rho": 120, "stair": 4, "reach": 20, "stop": 3, "phi": 30, "psi": 0, "advice": "verteilt", "mode": "bester", "block": 8, "seed": DEFAULT_SEED},
    "Anzeige für viele": {"rho": 120, "stair": 4, "reach": 20, "stop": 3, "phi": 0, "psi": 60, "advice": "ende", "mode": "bester", "block": 8, "seed": DEFAULT_SEED},
    "Alle laufen weit": {"rho": 100, "stair": 4, "reach": 80, "stop": 3, "phi": 0, "psi": 0, "advice": "ende", "mode": "bester", "block": 8, "seed": DEFAULT_SEED},
}
PRESET_HELP = {
    "Pendlerzug voll (Voreinstellung)": "Spitzenlast 120 % der Sitzplätze, mittlere Treppen-Bündelung, niemand außer Ihnen kennt den Tipp: Der Hinterzug ist leer.",
    "Halbleerer Zug": "Spitzenlast 80 %: Es gibt genug Plätze, der Tipp bringt kaum etwas (Messreihe: in der Mehrzahl der Zellen kein Vorsprung).",
    "Starke Treppe": "Bündelung 8 statt 4: Der Zug füllt sich noch einseitiger, der Tipp hat mehr Vorsprung und hält länger.",
    "Ohne Bündelung": "Negativkontrolle: Ohne Treppen-Bündelung verteilen sich die Fahrgäste gleichmäßig, der Tipp hat keinen Vorsprung.",
    "Jeder Dritte kennt den Tipp": "30 % der Mitreisenden gehen an die Türen des letzten Wagens: Der Hinterzug ist voll, der Tipp verliert.",
    "Breiter Tipp": "Auch 30 %, aber verteilt über die hintere Wagenhälfte: Der Tipp hält deutlich länger.",
    "Anzeige für viele": "60 % der Mitreisenden sehen die Auslastung bei Einfahrt und gehen alle zur besten Tür: Die Anzeige verliert ihren Vorsprung.",
    "Alle laufen weit": "Spitzenlast 100 %, die Mitreisenden laufen den ganzen Zug ab: Der Tipp hat keinen Vorsprung mehr (Grenze der Annahme).",
}
DEFAULT_PRESET = next(iter(PRESETS))
