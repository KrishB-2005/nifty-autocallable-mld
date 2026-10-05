"""Closed-form Black-Scholes / Black-76 prices and Greeks.

Everything is written in forward terms: an option on an index with forward F,
discount factor D and total implied variance w = sigma^2 T. That keeps term
structures of rates, dividends and vol exact (they only enter through F, D, w).
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm


def _d1d2(F, K, T, sigma):
    sd = sigma * np.sqrt(T)
    d1 = (np.log(F / K) + 0.5 * sd * sd) / sd
    return d1, d1 - sd


def black(F, K, T, sigma, df, kind="call"):
    """Black-76 price of a European call/put (vectorised)."""
    F, K, T, sigma, df = map(np.asarray, (F, K, T, sigma, df))
    d1, d2 = _d1d2(F, K, T, sigma)
    call = df * (F * norm.cdf(d1) - K * norm.cdf(d2))
    if kind == "call":
        return call
    if kind == "put":
        return call - df * (F - K)          # put-call parity
    raise ValueError(kind)


def bs_price(S, K, T, r, q, sigma, kind="call"):
    """Spot-form Black-Scholes-Merton with flat r, q."""
    F = S * np.exp((r - q) * T)
    return black(F, K, T, sigma, np.exp(-r * T), kind)


def bs_delta(S, K, T, r, q, sigma, kind="call"):
    d1, _ = _d1d2(S * np.exp((r - q) * T), K, T, sigma)
    dq = np.exp(-q * T)
    return dq * norm.cdf(d1) if kind == "call" else dq * (norm.cdf(d1) - 1.0)


def bs_gamma(S, K, T, r, q, sigma):
    d1, _ = _d1d2(S * np.exp((r - q) * T), K, T, sigma)
    return np.exp(-q * T) * norm.pdf(d1) / (S * sigma * np.sqrt(T))


def bs_vega(S, K, T, r, q, sigma):
    """dPrice/dsigma per unit vol (divide by 100 for per vol-point)."""
    d1, _ = _d1d2(S * np.exp((r - q) * T), K, T, sigma)
    return S * np.exp(-q * T) * norm.pdf(d1) * np.sqrt(T)


def black_digital(F, K, T, sigma, df, kind="call"):
    """Cash-or-nothing digital paying 1 if F_T > K (call) or < K (put)."""
    _, d2 = _d1d2(np.asarray(F), np.asarray(K), T, sigma)
    return df * (norm.cdf(d2) if kind == "call" else norm.cdf(-d2))


def black_asset_or_nothing(F, K, T, sigma, df, kind="call"):
    """Asset-or-nothing paying S_T if S_T > K (call) or < K (put)."""
    d1, _ = _d1d2(np.asarray(F), np.asarray(K), T, sigma)
    return df * F * (norm.cdf(d1) if kind == "call" else norm.cdf(-d1))


def implied_vol(price, F, K, T, df, kind="call", lo=1e-4, hi=3.0):
    """Black-76 implied vol by Brent. Returns nan if price is outside no-arb bounds."""
    intrinsic = df * max(F - K, 0.0) if kind == "call" else df * max(K - F, 0.0)
    upper = df * F if kind == "call" else df * K
    if not (intrinsic < price < upper):
        return np.nan
    f = lambda s: float(black(F, K, T, s, df, kind)) - price
    try:
        return brentq(f, lo, hi, xtol=1e-10)
    except ValueError:
        return np.nan
