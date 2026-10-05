"""Monte Carlo pricing of a European call/put, used as the correctness anchor
against the Black-Scholes closed form, plus pathwise and likelihood-ratio Greeks."""
from __future__ import annotations

import numpy as np

from .bs import black
from .market import Market
from .paths import make_grid, simulate
from .stats import MCResult, estimate


def closed_form(market: Market, K: float, T: float, kind: str = "call") -> float:
    return float(black(market.forward(T), K, T, market.vol.vol(T), market.curve.df(T), kind))


def mc_european(market: Market, K: float, T: float, n_paths: int, seed: int = 0,
                kind: str = "call", antithetic: bool = False) -> dict[str, MCResult]:
    """Price, delta and vega by MC. Returns a dict of MCResult keyed by
    'price', 'delta_pw', 'vega_pw' (pathwise), 'delta_lr', 'vega_lr' (likelihood ratio).
    Vega is per unit of vol."""
    grid = make_grid([T], daily=False)
    ps = simulate(market, grid, n_paths, seed, antithetic=antithetic, track_min=False, scores=True)
    S0 = market.spot
    ST = S0 * ps.rel_obs[:, 0]
    D = float(market.curve.df(T))
    sig = float(market.vol.vol(T))
    w = sig * sig * T
    F = float(market.forward(T))

    if kind == "call":
        itm = ST > K
        payoff = D * np.where(itm, ST - K, 0.0)
        sign = 1.0
    else:
        itm = ST < K
        payoff = D * np.where(itm, K - ST, 0.0)
        sign = -1.0

    # pathwise: d payoff/d theta = 1{ITM} * sign * dS_T/d theta
    dST_dS0 = ST / S0
    dST_dsig = ST * (np.log(ST / F) - 0.5 * w) / sig
    delta_pw = D * itm * sign * dST_dS0
    vega_pw = D * itm * sign * dST_dsig

    # likelihood ratio: payoff * score
    delta_lr = payoff * ps.score_delta / S0
    vega_lr = payoff * ps.score_vega

    pm = ps.pair_mean
    return {
        "price": estimate(pm(payoff)),
        "delta_pw": estimate(pm(delta_pw)),
        "vega_pw": estimate(pm(vega_pw)),
        "delta_lr": estimate(pm(delta_lr)),
        "vega_lr": estimate(pm(vega_lr)),
    }
