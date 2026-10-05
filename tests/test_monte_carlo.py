"""Monte Carlo against closed forms. Tolerances are 4 standard errors, so a
correct implementation fails about once in 16,000 runs per assertion."""
from dataclasses import replace

import numpy as np
import pytest

from mld.autocall import AutocallSpec, fair_coupon, price
from mld.bs import black, black_asset_or_nothing, black_digital, bs_delta, bs_vega
from mld.curve import DiscountCurve
from mld.market import Market, VolTermStructure
from mld.paths import make_grid, simulate
from mld.vanilla import closed_form, mc_european

Z = 4.0
FLAT = Market.flat(22421.95, 0.065, 0.0, 0.14)
TERM = Market(22421.95,
              DiscountCurve(np.array([0.5, 1, 3, 5]), np.array([0.056, 0.0585, 0.0645, 0.068])),
              DiscountCurve(np.array([1.0, 3.0]), np.array([-0.002, 0.003])),
              VolTermStructure(np.array([0.25, 1.0, 2.0]), np.array([0.13, 0.125, 0.14])))


def within(mc, target, z=Z):
    return abs(mc.value - target) <= z * mc.stderr


@pytest.mark.parametrize("market", [FLAT, TERM], ids=["flat", "term-structure"])
@pytest.mark.parametrize("kind", ["call", "put"])
def test_vanilla_mc_matches_black_scholes(market, kind):
    K, T = 23500.0, 2.5
    r = mc_european(market, K, T, 200_000, seed=11, kind=kind, antithetic=True)
    assert within(r["price"], closed_form(market, K, T, kind))


def test_pathwise_and_lr_greeks_match_closed_form():
    S, K, T = FLAT.spot, 23000.0, 3.0
    r = mc_european(FLAT, K, T, 400_000, seed=3)
    delta = bs_delta(S, K, T, 0.065, 0.0, 0.14)
    vega = bs_vega(S, K, T, 0.065, 0.0, 0.14)
    for key, target in [("delta_pw", delta), ("delta_lr", delta), ("vega_pw", vega), ("vega_lr", vega)]:
        assert within(r[key], target), key


def test_simulated_index_is_a_martingale_under_the_forward():
    grid = make_grid((1.0, 2.0, 3.0), steps_per_year=52)
    ps = simulate(TERM, grid, 100_000, seed=5)
    for k, t in enumerate((1.0, 2.0, 3.0)):
        x = ps.rel_obs[:, k]
        se = x.std() / np.sqrt(len(x))
        assert abs(x.mean() - TERM.forward(t) / TERM.spot) < Z * se


def test_same_seed_gives_same_paths_and_antithetics_pair_up():
    grid = make_grid((1.0,), daily=False)
    a = simulate(FLAT, grid, 1000, seed=9, antithetic=True, scores=True)
    b = simulate(FLAT.with_vol_shift(0.05), grid, 1000, seed=9, antithetic=True, scores=True)
    np.testing.assert_allclose(a.score_delta[:500], -a.score_delta[500:])
    np.testing.assert_allclose(a.score_delta * 0.14, b.score_delta * 0.19)  # same normals


def test_autocall_with_zero_rates_and_no_risk_is_exactly_par():
    m = Market.flat(22421.95, 0.0, 0.0, 0.2)
    spec = AutocallSpec(coupon_rate=0.0, ki_barrier=0.0)
    r = price(spec, m, 20_000, control=None)
    assert r.price.value == pytest.approx(100.0)
    assert r.price.stderr == pytest.approx(0.0, abs=1e-10)


def test_autocall_that_never_calls_or_knocks_in_is_the_zero_coupon_bond():
    spec = AutocallSpec(autocall_levels=1e9, ki_barrier=0.0)
    r = price(spec, TERM, 20_000, control=None, credit_spread=0.01)
    assert r.price.value == pytest.approx(r.zcb)
    assert r.overlay == pytest.approx(0.0, abs=1e-9)


def test_single_observation_note_matches_digital_decomposition():
    """One observation, barrier checked at maturity only. Then the note is
    100(1+cT) cash digitals above 100% (snowball coupon), 100 cash between B and 100%, and
    100/S_ref asset-or-nothing puts below B, all in closed form."""
    T, c, B = 2.0, 0.08, 0.7
    spec = AutocallSpec(obs_times=(T,), coupon_rate=c, ki_barrier=B, ki_daily=False)
    m = TERM
    S, F, D, v = m.spot, m.forward(T), m.curve.df(T), m.vol.vol(T)
    dig_ac = black_digital(F, S, T, v, D)
    dig_b = black_digital(F, B * S, T, v, D)
    aon_put = black_asset_or_nothing(F, B * S, T, v, D, "put")
    exact = 100 * (1 + c * T) * dig_ac + 100 * (dig_b - dig_ac) + 100 / S * aon_put
    r = price(spec, m, 400_000, seed=21, control=None)
    assert within(r.price, exact)


def test_control_variates_cut_error_without_bias():
    spec = AutocallSpec(ki_daily=False)
    plain = price(spec, TERM, 100_000, seed=4, antithetic=False, control=None)
    cv = price(spec, TERM, 100_000, seed=4, antithetic=True, control="full")
    assert cv.price.stderr < 0.6 * plain.price.stderr
    assert abs(cv.price.value - plain.price.value) < Z * np.hypot(cv.price.stderr, plain.price.stderr)


def test_fair_coupon_hits_the_target_price():
    spec = AutocallSpec(ki_daily=False)
    c = fair_coupon(spec, TERM, 98.0, 50_000, seed=8, credit_spread=0.01)
    r = price(replace(spec, coupon_rate=c), TERM, 50_000, seed=8, control=None, credit_spread=0.01)
    assert r.price.value == pytest.approx(98.0, abs=1e-9)
