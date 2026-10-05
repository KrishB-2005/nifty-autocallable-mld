"""Semi-analytic autocall pieces from multivariate normal probabilities.

Under deterministic rates, dividends and vol, the log index at the
observation dates X_k = ln(S(t_k)/S_ref) is jointly normal with

    mean_k = ln(F(t_k)/S_ref) - w(t_k)/2,   Cov(X_i, X_j) = w(min(t_i, t_j))

where w is total implied variance. Every autocall event is a box in X:
"called at t_2" is {X_1 < ln AC_1, X_2 >= ln AC_2}. Its cash value is a
discounted multivariate normal probability. Asset-settled pieces such as
S_T/S_ref on the loss branch use the share measure, under which each mean
shifts by Cov(X_k, X_n).

With a barrier checked only at the final fixing, the note is an exact linear
combination of these pieces: a closed form. With a daily barrier the same
pieces still carry almost all of the payoff, which makes them good control
variates. Only the "touched the barrier, then recovered above it" paths are
left to simulate.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import multivariate_normal

from .market import Market


def _moments(market: Market, times, s_ref):
    t = np.asarray(times, dtype=float)
    w = market.vol.total_var(t)
    mean = np.log(market.forward(t) / s_ref) - 0.5 * w
    cov = w[np.minimum.outer(np.arange(len(t)), np.arange(len(t)))]
    return mean, cov, w


def box_prob(mean, cov, lower, upper) -> float:
    """P(lower <= X <= upper) for X ~ N(mean, cov); infinite bounds allowed."""
    lower, upper = np.asarray(lower, float), np.asarray(upper, float)
    if len(mean) == 1:
        from scipy.stats import norm
        sd = np.sqrt(cov[0, 0])
        return float(norm.cdf((upper[0] - mean[0]) / sd) - norm.cdf((lower[0] - mean[0]) / sd))
    # scipy integrates with randomised QMC (Genz), so repeated calls differ by
    # about 1e-6 per 100 notional at this tolerance: 0.0001bp, and 0.4s per price.
    mvn = multivariate_normal(mean=mean, cov=cov, maxpts=500_000, abseps=1e-8, releps=1e-8)
    lower = np.where(np.isinf(lower), -1e3, lower)   # scipy needs finite lower limits
    return float(mvn.cdf(upper, lower_limit=lower))


def event_values(spec, market: Market, s_ref: float | None = None):
    """Risk-free discounted values of the payoff building blocks.

    Returns (call_k, survive_above_B, loss_asset):
      call_k[k]        D(t_k) P(not called before t_k, S(t_k) >= AC_k S_ref)
      survive_above_B  D(T)   P(never called, S(T) > B S_ref)
      loss_asset       D(T)   E[S(T)/S_ref ; never called, S(T) <= B S_ref]
    """
    s_ref = market.spot if s_ref is None else s_ref
    t = np.asarray(spec.obs_times, dtype=float)
    n = len(t)
    D = market.curve.df(t)
    ln_ac = np.log(spec.ac_levels)
    ln_b = np.log(spec.ki_barrier) if spec.ki_barrier > 0 else -np.inf
    mean, cov, w = _moments(market, t, s_ref)

    call_k = np.empty(n)
    for k in range(n):
        lo = np.concatenate([np.full(k, -np.inf), [ln_ac[k]]])
        hi = np.concatenate([ln_ac[:k], [np.inf]])
        call_k[k] = D[k] * box_prob(mean[:k + 1], cov[:k + 1, :k + 1], lo, hi)

    lo_surv = np.concatenate([np.full(n - 1, -np.inf), [ln_b]])
    hi_surv = ln_ac.copy()
    above_b = D[-1] * box_prob(mean, cov, lo_surv, hi_surv)

    # share measure for S(T): means shift by Cov(X_k, X_n) = w(t_k)
    mean_s = mean + cov[:, -1]
    hi_loss = np.concatenate([ln_ac[:-1], [min(ln_b, ln_ac[-1])]])
    fwd_ratio = market.forward(t[-1]) / s_ref
    loss_asset = D[-1] * fwd_ratio * box_prob(mean_s, cov, np.full(n, -np.inf), hi_loss)
    return call_k, above_b, loss_asset


def european_barrier_price(spec, market: Market, s_ref: float | None = None,
                           credit_spread: float = 0.0) -> float:
    """Closed-form value of the note when the knock-in is checked at the final
    fixing only. Credit spread scales each cash flow by exp(-s t)."""
    call_k, above_b, loss_asset = event_values(spec, market, s_ref)
    t = np.asarray(spec.obs_times, dtype=float)
    cs = np.exp(-credit_spread * t)
    N, c = spec.notional, spec.coupon_rate
    return float(np.sum(N * (1 + c * t) * call_k * cs) + N * (above_b + loss_asset) * cs[-1])


def event_controls(spec, ps, market: Market, s_ref: float):
    """Per-path discounted event payoffs matching `event_values`, as control variates."""
    spot = market.spot
    x = spot * ps.rel_obs / s_ref
    t = np.asarray(spec.obs_times, dtype=float)
    D = market.curve.df(t)
    ac = spec.ac_levels
    alive = np.ones(x.shape[0], dtype=bool)
    cols = []
    for k in range(x.shape[1]):
        hit = alive & (x[:, k] >= ac[k])
        cols.append(D[k] * hit)
        alive &= ~hit
    xT = x[:, -1]
    cols.append(D[-1] * (alive & (xT > spec.ki_barrier)))
    cols.append(D[-1] * xT * (alive & (xT <= spec.ki_barrier)))
    call_k, above_b, loss_asset = event_values(spec, market, s_ref)
    return np.column_stack(cols), np.concatenate([call_k, [above_b, loss_asset]])
