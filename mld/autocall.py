"""Autocallable market-linked debenture with a knock-in barrier.

Payoff, per 100 of face (levels are fractions of the initial fixing S_ref):

* On observation date t_k before maturity: if S(t_k) >= AC_k * S_ref the note
  redeems early at 100 * (1 + c * t_k)  ("snowball" coupon, accrued since issue).
* At maturity T, if not called:
    - S(T) >= AC_n * S_ref                       -> 100 * (1 + c * T)
    - otherwise, if the knock-in never triggered  -> 100
    - otherwise                                   -> 100 * min(1, S(T) / S_ref)
  The knock-in triggers if the index closes at or below B * S_ref on any day
  (daily monitoring) or at the final fixing only (European barrier).

Cash flows are discounted on the risk-free curve plus a flat issuer credit
spread, because the investor holds the issuer's unsecured paper. The index
itself drifts at the market forward (risk-neutral, funded at the risk-free rate).
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

from .bs import black, black_digital
from .curve import zero_coupon_bond
from .market import Market
from .paths import PathSummary, make_grid, simulate
from .stats import MCResult, estimate


@dataclass(frozen=True)
class AutocallSpec:
    notional: float = 100.0
    obs_times: tuple = (1.0, 2.0, 3.0)
    autocall_levels: float | tuple = 1.00
    coupon_rate: float = 0.09
    ki_barrier: float = 0.70
    ki_daily: bool = True

    @property
    def maturity(self) -> float:
        return float(self.obs_times[-1])

    @property
    def ac_levels(self) -> np.ndarray:
        return np.broadcast_to(np.asarray(self.autocall_levels, dtype=float), (len(self.obs_times),))


@dataclass
class AutocallResult:
    price: MCResult
    zcb: float                      # PV of 100 at maturity on the issuer curve
    prob_call: np.ndarray           # probability of redeeming with the coupon at each date (last = maturity)
    prob_ki: float                  # probability the barrier is ever breached
    prob_loss: float                # probability of getting back less than 100
    expected_life: float            # years
    method: str = ""
    extras: dict = field(default_factory=dict)

    @property
    def overlay(self) -> float:
        """Value of the derivative overlay = note - zero-coupon bond."""
        return self.price.value - self.zcb


def note_dfs(spec: AutocallSpec, market: Market, credit_spread: float) -> np.ndarray:
    t = np.asarray(spec.obs_times, dtype=float)
    return market.curve.df(t) * np.exp(-credit_spread * t)


def cashflows(spec: AutocallSpec, ps: PathSummary, spot: float, s_ref: float):
    """Per-path redemption amount (excluding coupon), coupon accrual factor and
    payment index. Splitting principal from coupon keeps PV linear in c."""
    x = spot * ps.rel_obs / s_ref                     # S(t_k) / S_ref
    n_obs = x.shape[1]
    ac = spec.ac_levels
    alive = np.ones(x.shape[0], dtype=bool)
    k_pay = np.full(x.shape[0], n_obs - 1)
    principal = np.full(x.shape[0], spec.notional)
    coupon_years = np.zeros(x.shape[0])

    for k in range(n_obs):
        called = alive & (x[:, k] >= ac[k])
        k_pay[called] = k
        coupon_years[called] = spec.obs_times[k]
        alive &= ~called

    xT = x[:, -1]
    if spec.ki_daily:
        knocked = spot * ps.rel_min / s_ref <= spec.ki_barrier
    else:
        knocked = xT <= spec.ki_barrier
    loss = alive & knocked
    principal[loss] = spec.notional * np.minimum(1.0, xT[loss])
    return principal, coupon_years, k_pay, knocked


def _control_set(spec, ps, market, spot, s_ref, which):
    """Discounted payoffs of hedge instruments with closed-form prices.

    'call' : the ATM vanilla call at maturity (the Layer-1 instrument).
    'full' : that call, plus a digital at each autocall trigger (these carry the
             early-redemption events) and puts struck at 100% and at the barrier
             (these carry the downside).
    """
    if which in (None, "none"):
        return None, None
    t = np.asarray(spec.obs_times, dtype=float)
    T = spec.maturity
    S = spot * ps.rel_obs
    D = market.curve.df(t)
    F = market.forward(t)
    vol = market.vol.vol(t)
    cols, mus = [], []

    K = s_ref
    cols.append(D[-1] * np.maximum(S[:, -1] - K, 0.0))
    mus.append(float(black(F[-1], K, T, vol[-1], D[-1], "call")))
    if which == "full":
        for k, ac in enumerate(spec.ac_levels):
            Kk = ac * s_ref
            cols.append(D[k] * (S[:, k] >= Kk))
            mus.append(float(black_digital(F[k], Kk, t[k], vol[k], D[k], "call")))
        for Kp in (s_ref, spec.ki_barrier * s_ref):
            cols.append(D[-1] * np.maximum(Kp - S[:, -1], 0.0))
            mus.append(float(black(F[-1], Kp, T, vol[-1], D[-1], "put")))
    elif which != "call":
        raise ValueError(which)
    return np.column_stack(cols), np.array(mus)


def apply_control_variates(y: np.ndarray, X: np.ndarray, mu: np.ndarray):
    """Regression control variate: y - (X - mu) beta, beta = Cov(X)^-1 Cov(X, y).
    Beta comes from the same sample, which adds an O(1/N) bias that is negligible
    next to the standard error at the path counts used here."""
    Xc = X - X.mean(axis=0)
    beta, *_ = np.linalg.lstsq(Xc, y - y.mean(), rcond=None)
    return y - (X - mu) @ beta, beta


def path_pv(spec: AutocallSpec, ps: PathSummary, market: Market, s_ref: float | None = None,
            credit_spread: float = 0.0):
    """Discounted payoff of every simulated path (before pairing antithetics)."""
    spot = market.spot
    s_ref = spot if s_ref is None else s_ref
    dfs = note_dfs(spec, market, credit_spread)
    principal, cyears, k_pay, knocked = cashflows(spec, ps, spot, s_ref)
    pv = dfs[k_pay] * (principal + spec.notional * spec.coupon_rate * cyears)
    return pv, principal, cyears, k_pay, knocked


def evaluate(spec: AutocallSpec, ps: PathSummary, market: Market, s_ref: float | None = None,
             credit_spread: float = 0.0, control: str | None = None) -> AutocallResult:
    """Value an already simulated set of paths at market.spot."""
    spot = market.spot
    s_ref = spot if s_ref is None else s_ref
    pv, principal, cyears, k_pay, knocked = path_pv(spec, ps, market, s_ref, credit_spread)

    pm = ps.pair_mean
    y = pm(pv)
    X, mu = _control_set(spec, ps, market, spot, s_ref, control)
    extras = {}
    if X is not None:
        y, beta = apply_control_variates(y, pm(X), mu)
        extras["beta"] = beta

    n_obs = len(spec.obs_times)
    called_early = cyears > 0
    prob_call = np.array([np.mean(called_early & (k_pay == k)) for k in range(n_obs)])
    t = np.asarray(spec.obs_times, dtype=float)
    return AutocallResult(
        price=estimate(y),
        zcb=zero_coupon_bond(market.curve, spec.maturity, spec.notional, credit_spread),
        prob_call=prob_call,
        prob_ki=float(np.mean(knocked)),
        prob_loss=float(np.mean(principal < spec.notional - 1e-12)),
        expected_life=float(np.mean(t[k_pay])),
        method=f"antithetic={ps.antithetic}, control={control}",
        extras=extras,
    )


def simulate_for(spec: AutocallSpec, market: Market, n_paths: int, seed: int = 0,
                 antithetic: bool = False, scores: bool = False,
                 steps_per_year: int = 252) -> PathSummary:
    grid = make_grid(spec.obs_times, steps_per_year, daily=spec.ki_daily)
    return simulate(market, grid, n_paths, seed, antithetic=antithetic,
                    track_min=spec.ki_daily, scores=scores)


def price(spec: AutocallSpec, market: Market, n_paths: int = 200_000, seed: int = 0,
          antithetic: bool = True, control: str | None = "full", credit_spread: float = 0.0,
          s_ref: float | None = None, steps_per_year: int = 252) -> AutocallResult:
    ps = simulate_for(spec, market, n_paths, seed, antithetic, steps_per_year=steps_per_year)
    return evaluate(spec, ps, market, s_ref, credit_spread, control)


def fair_coupon(spec: AutocallSpec, market: Market, target_price: float, n_paths: int = 200_000,
                seed: int = 0, credit_spread: float = 0.0, steps_per_year: int = 252) -> float:
    """Coupon rate that makes the note worth `target_price` (e.g. 100 minus the
    structuring margin). PV is linear in c on a fixed set of paths, so two
    valuations give the exact solution for that path set."""
    ps = simulate_for(spec, market, n_paths, seed, antithetic=True, steps_per_year=steps_per_year)
    v0 = evaluate(replace(spec, coupon_rate=0.0), ps, market, credit_spread=credit_spread).price.value
    v1 = evaluate(replace(spec, coupon_rate=1.0), ps, market, credit_spread=credit_spread).price.value
    return (target_price - v0) / (v1 - v0)
