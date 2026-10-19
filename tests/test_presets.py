"""Presets: Vollständigkeit, gültige Werte, Standard-Preset = Standardeinstellungen; Permalink-Begrenzung; Umrechnung in Modellparameter."""

import pytest

import stz_constants as C
import stz_evaluation as ev
import stz_presets as P


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP)
    for name, preset in C.PRESETS.items():
        assert set(preset) == set(P.PRESET_KEYS), name
        assert C.PRESET_HELP[name]


def test_preset_values_are_inside_the_slider_bounds_and_options():
    for name, preset in C.PRESETS.items():
        for key, state_key in P.PRESET_KEYS.items():
            spec = P.SETTING_SPECS[state_key]
            value = preset[key]
            if spec.options is not None:
                assert value in spec.options, (name, key)
            else:
                assert spec.lo <= value <= spec.hi, (name, key)


def test_default_preset_equals_the_default_settings():
    p = C.PRESETS[C.DEFAULT_PRESET]
    assert ev.Settings(**p) == ev.Settings()


def test_setting_specs_cover_every_preset_key():
    assert set(P.PRESET_KEYS.values()) == set(P.SETTING_SPECS)


def test_sliders_run_in_steps_of_ten_and_include_the_presets():
    for key, lo, hi in (("rho", C.RHO_MIN, C.RHO_MAX), ("phi", C.PHI_MIN, C.PHI_MAX), ("psi", C.PSI_MIN, C.PSI_MAX)):
        assert (lo, hi) == (min(lo, hi), max(lo, hi)) and lo % 10 == 0 and hi % 10 == 0
        assert all(p[key] % 10 == 0 for p in C.PRESETS.values())


def test_clamp_value_limits_numbers_and_discards_unknown_options():
    s_rho, s_stair, s_advice = (P.SETTING_SPECS[k] for k in ("rho_slider", "stair_select", "advice_radio"))
    assert P.clamp_value(s_rho, 10) == C.RHO_MIN and P.clamp_value(s_rho, 999) == C.RHO_MAX and P.clamp_value(s_rho, 100) == 100
    assert P.clamp_value(s_stair, 4) == 4 and P.clamp_value(s_stair, 5) == s_stair.default
    assert P.clamp_value(s_advice, "verteilt") == "verteilt" and P.clamp_value(s_advice, "x") == s_advice.default


def test_to_params_converts_percent_and_blockade():
    p = ev.to_params(ev.Settings(rho=120, stair=8, reach=40, phi=30, psi=60, advice="verteilt", mode="gewichtet", block=0))
    assert (p.rho, p.stair_a, p.reach_naive, p.phi, p.psi) == (1.2, 8.0, 40, 0.3, 0.6)
    assert p.advice == "verteilt" and p.blick_mode == "gewichtet" and p.block is None
    assert ev.to_params(ev.Settings(block=4)).block == 4


def test_seeds_of_different_settings_do_not_overlap():
    a, b = ev.seed0(ev.Settings(seed=1)), ev.seed0(ev.Settings(seed=2))
    assert b - a == 1000 and a >= C.SEED_BASE


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_is_a_valid_model_setting(name):
    p = ev.to_params(ev.Settings(**C.PRESETS[name]))
    assert 0 <= p.phi <= 1 and 0 <= p.psi <= 1 and p.rho > 0
