import numpy as np
import pytest

from mld.analytic import european_barrier_price
from mld.autocall import AutocallSpec, price
from mld.bs import black_asset_or_nothing, black_digital
from test_monte_carlo import TERM

SPECS = [
    AutocallSpec(ki_daily=False),
    AutocallSpec(ki_daily=False, autocall_levels=(1.0, 0.95, 0.90), ki_barrier=0.60, coupon_rate=0.11),
    AutocallSpec(ki_daily=False, obs_times=(0.5, 1.0, 1.5, 2.0), autocall_levels=1.05, ki_barrier=0.75),
]


def test_one_observation_reduces_to_black_scholes_digitals():
    T, c, B = 2.0, 0.08, 0.7
    spec = AutocallSpec(obs_times=(T,), coupon_rate=c, ki_barrier=B, ki_daily=False)
    S, F, D, v = TERM.spot, TERM.forward(T), TERM.curve.df(T), TERM.vol.vol(T)
    dig_ac, dig_b = black_digital(F, S, T, v, D), black_digital(F, B * S, T, v, D)
    exact = 100 * (1 + c * T) * dig_ac + 100 * (dig_b - dig_ac) + 100 / S * black_asset_or_nothing(F, B * S, T, v, D, "put")
    assert european_barrier_price(spec, TERM) == pytest.approx(exact, abs=1e-10)


@pytest.mark.parametrize("spec", SPECS, ids=["base", "step-down", "semiannual"])
def test_closed_form_matches_plain_monte_carlo(spec):
    exact = european_barrier_price(spec, TERM, credit_spread=0.01)
    mc = price(spec, TERM, 300_000, seed=17, antithetic=False, control=None, credit_spread=0.01).price
    assert abs(mc.value - exact) < 4 * mc.stderr


def test_event_controls_make_the_final_fixing_note_exact():
    spec = SPECS[0]
    r = price(spec, TERM, 20_000, seed=1, control="events", credit_spread=0.01)
    # equal up to the integration noise of the multivariate normal CDF
    assert r.price.value == pytest.approx(european_barrier_price(spec, TERM, credit_spread=0.01), abs=1e-5)
    assert r.price.stderr < 1e-8


def test_event_controls_beat_vanilla_controls_on_the_daily_barrier():
    spec = AutocallSpec(ki_daily=True)
    full = price(spec, TERM, 60_000, seed=2, control="full").price
    ev = price(spec, TERM, 60_000, seed=2, control="events").price
    assert ev.stderr < 0.6 * full.stderr
    assert abs(ev.value - full.value) < 4 * np.hypot(ev.stderr, full.stderr)
