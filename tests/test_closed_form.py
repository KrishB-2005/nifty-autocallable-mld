import numpy as np
import pytest

from mld.bs import (black, black_asset_or_nothing, black_digital, bs_delta, bs_gamma, bs_price,
                    bs_vega, implied_vol)
from mld.curve import DiscountCurve, zero_coupon_bond

S, K, T, r, q, vol = 22421.95, 23000.0, 2.0, 0.065, 0.01, 0.15


def test_curve_reprices_nodes_and_interpolates_log_linearly():
    c = DiscountCurve(np.array([1.0, 3.0]), np.array([0.06, 0.07]))
    assert c.df(1.0) == pytest.approx(np.exp(-0.06))
    assert c.df(3.0) == pytest.approx(np.exp(-0.21))
    # halfway in time is halfway in log DF
    assert np.log(c.df(2.0)) == pytest.approx(0.5 * (-0.06 - 0.21))
    # flat zero rate outside the nodes
    assert c.zero(0.5) == pytest.approx(0.06)
    assert c.zero(5.0) == pytest.approx(0.07)


def test_zero_coupon_bond_with_spread():
    c = DiscountCurve.flat(0.065)
    assert zero_coupon_bond(c, 3.0, 100, 0.01) == pytest.approx(100 * np.exp(-0.075 * 3))
    assert zero_coupon_bond(c.shifted(100), 3.0) == pytest.approx(100 * np.exp(-0.075 * 3))


def test_put_call_parity():
    c = bs_price(S, K, T, r, q, vol, "call")
    p = bs_price(S, K, T, r, q, vol, "put")
    assert c - p == pytest.approx(S * np.exp(-q * T) - K * np.exp(-r * T))


def test_greeks_match_bumped_closed_form():
    h = 1e-3
    up, dn = bs_price(S * (1 + h), K, T, r, q, vol), bs_price(S * (1 - h), K, T, r, q, vol)
    assert bs_delta(S, K, T, r, q, vol) == pytest.approx((up - dn) / (2 * S * h), rel=1e-5)
    mid = bs_price(S, K, T, r, q, vol)
    assert bs_gamma(S, K, T, r, q, vol) == pytest.approx((up - 2 * mid + dn) / (S * h) ** 2, rel=1e-4)
    vu, vd = bs_price(S, K, T, r, q, vol + 1e-4), bs_price(S, K, T, r, q, vol - 1e-4)
    assert bs_vega(S, K, T, r, q, vol) == pytest.approx((vu - vd) / 2e-4, rel=1e-6)


def test_digital_is_minus_strike_derivative_of_call():
    F, D, h = S * np.exp((r - q) * T), np.exp(-r * T), 0.01
    dcdk = (black(F, K + h, T, vol, D) - black(F, K - h, T, vol, D)) / (2 * h)
    assert black_digital(F, K, T, vol, D) == pytest.approx(-dcdk, rel=1e-6)


def test_asset_and_cash_digitals_rebuild_the_call():
    F, D = S * np.exp((r - q) * T), np.exp(-r * T)
    rebuilt = black_asset_or_nothing(F, K, T, vol, D) - K * black_digital(F, K, T, vol, D)
    assert rebuilt == pytest.approx(black(F, K, T, vol, D))


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("strike", [16000.0, 22421.95, 30000.0])
def test_implied_vol_round_trip(kind, strike):
    F, D = S * np.exp((r - q) * T), np.exp(-r * T)
    price = float(black(F, strike, T, 0.21, D, kind))
    assert implied_vol(price, F, strike, T, D, kind) == pytest.approx(0.21, abs=1e-8)


def test_implied_vol_rejects_arbitrage_prices():
    F, D = 100.0, 0.95
    assert np.isnan(implied_vol(0.0, F, 120.0, 1.0, D, "call"))
    assert np.isnan(implied_vol(D * F + 1, F, 120.0, 1.0, D, "call"))
