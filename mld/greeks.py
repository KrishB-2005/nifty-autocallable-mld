"""Greeks of the autocallable.

Finite differences with common random numbers (CRN): the bumped and base
valuations reuse the same normals, so the noise largely cancels in the
difference. Spot bumps do not even need a new simulation, since paths are
stored relative to spot. The standard error comes from the per-path differences.

Likelihood ratio (LR): Greek = E[payoff x score], where the score is the
derivative of the log path density. It handles the digital-like jumps in the
autocall payoff that break pathwise differentiation, but its variance grows as
the first time step shrinks (delta) and with the number of steps (vega), so it
only competes with FD-CRN on a coarse grid (European knock-in).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .autocall import AutocallSpec, path_pv, simulate_for
from .market import Market
from .stats import MCResult, estimate


@dataclass
class Greeks:
    price: MCResult
    delta: MCResult      # per 1 index point
    gamma: MCResult      # per 1 index point^2
    vega: MCResult       # per 1 vol point (0.01)

    def delta_pct(self, spot):
        """Price change for a 1% spot move."""
        return self.delta.value * spot * 0.01


def fd_greeks(spec: AutocallSpec, market: Market, n_paths: int = 200_000, seed: int = 0,
              s_ref: float | None = None, credit_spread: float = 0.0,
              spot_bump: float = 0.01, vol_bump: float = 0.01,
              antithetic: bool = True) -> Greeks:
    S = market.spot
    s_ref = S if s_ref is None else s_ref
    ps = simulate_for(spec, market, n_paths, seed, antithetic)
    pm = ps.pair_mean
    pv = lambda m, p: pm(path_pv(spec, p, m, s_ref, credit_spread)[0])

    h = S * spot_bump
    v0 = pv(market, ps)
    vu = pv(market.with_spot(S + h), ps)
    vd = pv(market.with_spot(S - h), ps)

    ps_vu = simulate_for(spec, market.with_vol_shift(vol_bump), n_paths, seed, antithetic)
    ps_vd = simulate_for(spec, market.with_vol_shift(-vol_bump), n_paths, seed, antithetic)
    wu = pv(market.with_vol_shift(vol_bump), ps_vu)
    wd = pv(market.with_vol_shift(-vol_bump), ps_vd)

    return Greeks(
        price=estimate(v0),
        delta=estimate((vu - vd) / (2 * h)),
        gamma=estimate((vu - 2 * v0 + vd) / (h * h)),
        vega=estimate((wu - wd) / (2 * vol_bump) * 0.01),
    )


def lr_greeks(spec: AutocallSpec, market: Market, n_paths: int = 200_000, seed: int = 0,
              s_ref: float | None = None, credit_spread: float = 0.0,
              antithetic: bool = True) -> dict[str, MCResult]:
    """Delta and vega (per vol point) by the likelihood-ratio method.

    The vega score is for a parallel shift of every step volatility, which is a
    parallel shift of implied vol when the term structure is flat."""
    S = market.spot
    ps = simulate_for(spec, market, n_paths, seed, antithetic, scores=True)
    pv = path_pv(spec, ps, market, s_ref, credit_spread)[0]
    pm = ps.pair_mean
    return {
        "delta": estimate(pm(pv * ps.score_delta / S)),
        "vega": estimate(pm(pv * ps.score_vega) * 0.01),
    }
