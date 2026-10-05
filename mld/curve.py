"""Discount curves and the zero-coupon bond leg.

Conventions: continuous compounding, ACT/365F year fractions, log-linear
interpolation of discount factors (= piecewise-constant forward rates), flat
zero-rate extrapolation on both ends. Inside the node range this is exactly
QuantLib's ``DiscountCurve(dates, dfs, Actual365Fixed())`` (log-linear on DF),
which ``validation/quantlib_check.py`` verifies node-for-node.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DiscountCurve:
    tenors: np.ndarray       # year fractions, strictly increasing, > 0
    zero_rates: np.ndarray   # continuously compounded

    def __post_init__(self):
        t = np.asarray(self.tenors, dtype=float)
        z = np.asarray(self.zero_rates, dtype=float)
        if t.ndim != 1 or t.shape != z.shape or np.any(np.diff(t) <= 0) or t[0] <= 0:
            raise ValueError("tenors must be 1-D, positive, strictly increasing, same shape as rates")
        object.__setattr__(self, "tenors", t)
        object.__setattr__(self, "zero_rates", z)

    @classmethod
    def flat(cls, rate: float) -> "DiscountCurve":
        return cls(np.array([1.0, 50.0]), np.array([rate, rate]))

    def _log_df(self, t):
        t = np.asarray(t, dtype=float)
        rt = self.zero_rates * self.tenors           # -ln DF at the nodes
        # linear in r*t between nodes; flat zero rate outside
        inner = np.interp(t, self.tenors, rt)
        lo = self.zero_rates[0] * t
        hi = self.zero_rates[-1] * t
        out = np.where(t < self.tenors[0], lo, np.where(t > self.tenors[-1], hi, inner))
        return -out

    def df(self, t):
        return np.exp(self._log_df(t))

    def zero(self, t):
        t = np.asarray(t, dtype=float)
        return np.where(t > 0, -self._log_df(np.maximum(t, 1e-12)) / np.maximum(t, 1e-12), self.zero_rates[0])

    def forward(self, t1, t2):
        """Continuously compounded forward rate between t1 and t2."""
        return (self._log_df(t1) - self._log_df(t2)) / (np.asarray(t2) - np.asarray(t1))

    def shifted(self, bp: float) -> "DiscountCurve":
        """Parallel shift of the zero curve in basis points."""
        return DiscountCurve(self.tenors, self.zero_rates + bp * 1e-4)


def zero_coupon_bond(curve: DiscountCurve, maturity: float, notional: float = 100.0,
                     credit_spread: float = 0.0) -> float:
    """PV of a bullet repayment of `notional` at `maturity`, discounted on the
    risk-free curve plus a flat issuer credit spread (continuous)."""
    return float(notional * curve.df(maturity) * np.exp(-credit_spread * maturity))
