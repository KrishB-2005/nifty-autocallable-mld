"""Scenario analysis: spot x vol revaluation grid and named stress tests.

Scenarios are instantaneous shocks just after issue: the initial fixing
S_ref stays where it was struck and the market moves. Every scenario reuses
the same seed (common random numbers), so the surface is smooth and the
differences between cells are not Monte Carlo noise.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .autocall import AutocallSpec, evaluate, simulate_for
from .market import Market


def spot_vol_grid(spec: AutocallSpec, market: Market, spot_levels, vol_shifts,
                  n_paths: int = 100_000, seed: int = 0, credit_spread: float = 0.0,
                  s_ref: float | None = None) -> pd.DataFrame:
    """Note value for each (spot level as % of S_ref, parallel vol shift).

    One simulation per vol level; paths are relative to spot, so every spot
    level on that row is a revaluation of the same paths."""
    s_ref = market.spot if s_ref is None else s_ref
    out = np.empty((len(vol_shifts), len(spot_levels)))
    for i, dv in enumerate(vol_shifts):
        m = market.with_vol_shift(dv)
        ps = simulate_for(spec, m, n_paths, seed, antithetic=True)
        for j, x in enumerate(spot_levels):
            out[i, j] = evaluate(spec, ps, m.with_spot(s_ref * x), s_ref, credit_spread).price.value
    return pd.DataFrame(out, index=pd.Index(vol_shifts, name="vol_shift"),
                        columns=pd.Index(spot_levels, name="spot_level"))


@dataclass(frozen=True)
class Stress:
    name: str
    spot: float = 1.0          # multiple of current spot
    vol: float = 0.0           # parallel shift, absolute (0.10 = +10 vol points)
    rates_bp: float = 0.0      # parallel shift of the INR curve
    spread_bp: float = 0.0     # change in issuer credit spread


DEFAULT_STRESSES = [
    Stress("Base"),
    Stress("Spot -10%", spot=0.90),
    Stress("Spot -20%", spot=0.80),
    Stress("Spot -30% (at the barrier)", spot=0.70),
    Stress("Vol +5 pts", vol=0.05),
    Stress("Vol -3 pts", vol=-0.03),
    Stress("Rates +100bp", rates_bp=100),
    Stress("Issuer spread +200bp", spread_bp=200),
    Stress("Mar-2020 style: spot -35%, vol +25 pts", spot=0.65, vol=0.25),
    Stress("Taper tantrum: spot -10%, vol +8, rates +150bp", spot=0.90, vol=0.08, rates_bp=150),
    Stress("Issuer stress: spot -20%, vol +10, spread +400bp", spot=0.80, vol=0.10, spread_bp=400),
]


def stress_table(spec: AutocallSpec, market: Market, stresses=DEFAULT_STRESSES,
                 n_paths: int = 100_000, seed: int = 0, credit_spread: float = 0.0) -> pd.DataFrame:
    s_ref = market.spot
    rows, base = [], None
    for s in stresses:
        m = market.with_vol_shift(s.vol).with_rate_shift(s.rates_bp).with_spot(s_ref * s.spot)
        ps = simulate_for(spec, m, n_paths, seed, antithetic=True)
        r = evaluate(spec, ps, m, s_ref, credit_spread + s.spread_bp * 1e-4)
        base = r.price.value if base is None else base
        rows.append(dict(scenario=s.name, price=r.price.value, pnl=r.price.value - base,
                         prob_call_1y=r.prob_call[0], prob_ki=r.prob_ki, prob_loss=r.prob_loss,
                         expected_life=r.expected_life))
    return pd.DataFrame(rows)
