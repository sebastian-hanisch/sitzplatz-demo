"""Permalink (Begrenzen/Einrasten), Presets und Zufalls-Seed-Button (Standardmuster aus dem Demo-Portfolio)."""

import random
from dataclasses import dataclass

import streamlit as st

import stz_constants as C


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: type
    default: object
    lo: float | None = None
    hi: float | None = None
    options: tuple | None = None     # erlaubte Werte (select_slider, radio): ein Permalink mit anderem Wert wird auf den Standard gesetzt


P0 = C.PRESETS[C.DEFAULT_PRESET]
SETTING_SPECS = {
    "rho_slider": SettingSpec("last", int, P0["rho"], C.RHO_MIN, C.RHO_MAX),
    "stair_select": SettingSpec("treppe", int, P0["stair"], options=C.STAIR_OPTIONS),
    "reach_select": SettingSpec("reichweite", int, P0["reach"], options=C.REACH_OPTIONS),
    "stop_slider": SettingSpec("halt", int, P0["stop"], C.STOP_MIN, C.STOP_MAX),
    "phi_slider": SettingSpec("tipp", int, P0["phi"], C.PHI_MIN, C.PHI_MAX),
    "psi_slider": SettingSpec("anzeige", int, P0["psi"], C.PSI_MIN, C.PSI_MAX),
    "advice_radio": SettingSpec("tippart", str, P0["advice"], options=C.ADVICE_OPTIONS),
    "mode_radio": SettingSpec("modus", str, P0["mode"], options=C.MODE_OPTIONS),
    "block_select": SettingSpec("gang", int, P0["block"], options=C.BLOCK_OPTIONS),
    "seed_input": SettingSpec("seed", int, P0["seed"], 0, C.SEED_MAX),
}
PRESET_KEYS = {"rho": "rho_slider", "stair": "stair_select", "reach": "reach_select", "stop": "stop_slider", "phi": "phi_slider",
               "psi": "psi_slider", "advice": "advice_radio", "mode": "mode_radio", "block": "block_select", "seed": "seed_input"}


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def clamp_value(spec, value):
    """Wert eines Permalinks auf den Regler abbilden: Zahlen begrenzen, Auswahlwerte außerhalb der Optionen verwerfen."""
    if spec.options is not None:
        return value if value in spec.options else spec.default
    if spec.lo is not None:
        value = max(spec.lo, value)
    if spec.hi is not None:
        value = min(spec.hi, value)
    return value


def load_permalink_settings():
    """Einmal je Sitzung: Werte aus der Adresszeile übernehmen, auf die Reglergrenzen begrenzt."""
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            try:
                value = spec.caster(qp[spec.url_param])
            except (ValueError, TypeError):
                continue
            st.session_state[state_key] = clamp_value(spec, value)
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    """`values`: {state_key: aktueller Wert}; die Adresszeile spiegelt die Konfiguration."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = str(value)
    except Exception:
        pass


def apply_preset(name):
    for key, state_key in PRESET_KEYS.items():
        if key in C.PRESETS[name]:
            st.session_state[state_key] = C.PRESETS[name][key]


def aktives_preset():
    """Name des Presets, dessen Werte GENAU den aktuellen Einstellungen entsprechen, sonst None.

    Zustandslos: verglichen wird jeder Regler aus SETTING_SPECS (ein Preset ohne Eintrag für einen Regler meint dessen
    Standardwert) mit dem Session State. Ein später ergänzter Regler braucht nur seinen Eintrag in SETTING_SPECS,
    dann hebt auch seine Änderung die Markierung auf (tests/test_layout.py prüft das für jeden Regler)."""
    preset_key_of = {state_key: key for key, state_key in PRESET_KEYS.items()}
    for name, preset in C.PRESETS.items():
        if all(
            st.session_state.get(state_key, spec.default) == preset.get(preset_key_of.get(state_key), spec.default)
            for state_key, spec in SETTING_SPECS.items()
        ):
            return name
    return None


def sidebar_presets():
    """Schnellstart oben in der Seitenleiste; das aktive Preset ist hervorgehoben (`type="primary"`)."""
    if not C.PRESETS:
        return
    st.header("🎯 Schnellstart")
    st.caption("Ein Beispielszenario laden:")
    aktiv = aktives_preset()
    for name in C.PRESETS:
        st.button(
            name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP.get(name, ""), key=f"preset_{name}",
            type="primary" if aktiv == name else "secondary",
        )


def randomize_seed():
    st.session_state["seed_input"] = random.randint(0, C.SEED_MAX)
