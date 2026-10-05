"""GBM path simulation with deterministic rate, dividend and vol term structures.

Each step uses the exact lognormal transition, so there is no time
discretisation bias at grid points:

    ln S(t_i) = ln S(t_{i-1}) + ln[F(t_i)/F(t_{i-1})] - v_i/2 + sqrt(v_i) Z_i

where F is the market forward and v_i = w(t_i) - w(t_{i-1}) is the forward
implied variance. Paths are stored relative to spot (S/S0), so one simulation
can be revalued at any spot, which is what the scenario grid and spot bumps use.

Only what payoffs need is kept: S/S0 at observation dates and the running
minimum up to each observation date (for a knock-in barrier, which only
matters while the note is alive). Full paths would be 756 steps x N floats.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .market import Market


@dataclass(frozen=True)
class TimeGrid:
    times: np.ndarray     # starts at 0, includes every observation date
    obs_idx: np.ndarray   # indices of observation dates in `times`

    @property
    def dt(self):
        return np.diff(self.times)


def make_grid(obs_times, steps_per_year: int = 252, daily: bool = True) -> TimeGrid:
    """Grid that hits every observation date exactly.

    daily=True subdivides each period into ~steps_per_year steps per year
    (needed when a barrier is monitored on daily closes); daily=False steps
    straight from one observation date to the next.
    """
    times, obs_idx, prev = [0.0], [], 0.0
    for t in obs_times:
        n = max(1, int(round((t - prev) * steps_per_year))) if daily else 1
        times.extend(np.linspace(prev, t, n + 1)[1:])
        obs_idx.append(len(times) - 1)
        prev = t
    return TimeGrid(np.array(times), np.array(obs_idx))


@dataclass
class PathSummary:
    rel_obs: np.ndarray            # (N, n_obs) S(t_k)/S0
    rel_min: np.ndarray | None     # (N, n_obs) running min of S/S0 up to each observation date
    score_delta: np.ndarray | None  # (N,) d ln p / d ln S0 = Z_1 / (sigma_1 sqrt(dt_1))
    score_vega: np.ndarray | None   # (N,) d ln p / d sigma for a parallel shift of step vols
    antithetic: bool

    @property
    def n(self):
        return self.rel_obs.shape[0]

    def pair_mean(self, x):
        """Collapse antithetic pairs into i.i.d. samples (first half + second half)."""
        if not self.antithetic:
            return x
        h = x.shape[0] // 2
        return 0.5 * (x[:h] + x[h:])


def step_params(market: Market, grid: TimeGrid):
    """Per-step log-drift and stdev implied by the market's forward and variance curves."""
    t = grid.times
    fwd = market.div.df(t) / market.curve.df(t)          # F(t)/S0
    w = market.vol.total_var(t)
    var = np.diff(w)
    drift = np.diff(np.log(fwd)) - 0.5 * var
    return drift, np.sqrt(var)


def simulate(market: Market, grid: TimeGrid, n_paths: int, seed: int = 0,
             antithetic: bool = False, track_min: bool = True, scores: bool = False,
             batch_size: int = 100_000) -> PathSummary:
    """Simulate n_paths relative paths. Same seed + same batch_size gives the
    same normals whatever the market, so bumped revaluations share randomness."""
    drift, sd = step_params(market, grid)
    dt = grid.dt
    sigma = sd / np.sqrt(dt)
    rng = np.random.default_rng(seed)
    n_obs = len(grid.obs_idx)
    obs_pos = {int(i): k for k, i in enumerate(grid.obs_idx)}

    plus, minus = [], []
    remaining = n_paths
    while remaining > 0:
        b = min(batch_size, remaining)
        if antithetic and b % 2:
            b += 1
        h = b // 2 if antithetic else b
        x = np.zeros(b)
        mn = np.zeros(b) if track_min else None
        obs = np.empty((b, n_obs))
        mins = np.empty((b, n_obs)) if track_min else None
        s_delta = np.zeros(b) if scores else None
        s_vega = np.zeros(b) if scores else None
        for i in range(len(dt)):
            z = rng.standard_normal(h)
            if antithetic:
                z = np.concatenate([z, -z])
            x += drift[i] + sd[i] * z
            if track_min:
                np.minimum(mn, x, out=mn)
            if scores:
                if i == 0:
                    s_delta = z / sd[0]
                s_vega += (z * z - 1.0) / sigma[i] - z * np.sqrt(dt[i])
            k = obs_pos.get(i + 1)
            if k is not None:
                obs[:, k] = x
                if track_min:
                    mins[:, k] = mn
        parts = [np.exp(obs), np.exp(mins) if track_min else None, s_delta, s_vega]
        if antithetic:
            plus.append([p[:h] if p is not None else None for p in parts])
            minus.append([p[h:] if p is not None else None for p in parts])
        else:
            plus.append(parts)
        remaining -= b

    blocks = plus + minus
    cat = lambda j: None if blocks[0][j] is None else np.concatenate([blk[j] for blk in blocks])
    return PathSummary(cat(0), cat(1), cat(2), cat(3), antithetic)
