"""AppTest für die Regler, die der Smoke-Test der Vorlage nicht anfasst: Auswahl-Regler (Grenzen und alle Optionen am Rand), Radios, Zahleneingabe.

Die Vorlage fährt nur `st.slider` an Minimum und Maximum; die Optionsregler dieser App (Bündelung, Reichweite, Gang) und die Radios
(Tipp-Art, Anzeige-Modus) sind sonst ungeprüft (Memory: Smoke-Test-Vorlage nur st.slider)."""

import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import stz_constants as C

APP = str(Path(__file__).resolve().parent.parent / "app.py")
TIMEOUT = int(os.environ.get("APPTEST_TIMEOUT", "300"))


def _app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    return at


@pytest.mark.parametrize("key,options", [("stair_select", C.STAIR_OPTIONS), ("reach_select", C.REACH_OPTIONS), ("block_select", C.BLOCK_OPTIONS)])
def test_select_sliders_at_both_ends_and_in_the_middle_do_not_raise(key, options):
    at = _app()
    for value in (options[0], options[-1], options[len(options) // 2]):
        at.sidebar.select_slider(key=key).set_value(value).run()
        assert not at.exception, (key, value, [str(e) for e in at.exception])
        assert at.session_state[key] == value


@pytest.mark.parametrize("radio,steuer,options", [("advice_radio", "phi_slider", C.ADVICE_OPTIONS), ("mode_radio", "psi_slider", C.MODE_OPTIONS)])
def test_radios_work_once_their_share_is_positive(radio, steuer, options):
    at = _app()
    at.sidebar.slider(key=steuer).set_value(30).run()
    for value in reversed(options):
        at.sidebar.radio(key=radio).set_value(value).run()
        assert not at.exception, (radio, value, [str(e) for e in at.exception])
        assert at.session_state[radio] == value


def test_seed_input_at_the_bounds_does_not_raise():
    at = _app()
    for value in (0, C.SEED_MAX):
        at.sidebar.number_input(key="seed_input").set_value(value).run()
        assert not at.exception, (value, [str(e) for e in at.exception])


def test_permalink_is_clamped_and_unknown_options_fall_back_to_the_default():
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.query_params["last"] = "999"        # über dem Maximum
    at.query_params["treppe"] = "5"        # keine Option
    at.query_params["tippart"] = "x"       # keine Option
    at.run()
    assert not at.exception
    assert at.session_state["rho_slider"] == C.RHO_MAX
    assert at.session_state["stair_select"] == C.DEFAULT_STAIR
    assert at.session_state["advice_radio"] == "ende"
