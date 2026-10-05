"""Market state: spot, discount curve, dividend/carry curve, vol term structure."""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from .curve import DiscountCurve


@dataclass(frozen=True)
class VolTermStructure:
    """Deterministic implied-vol term structure (no smile).

    Interpolates total variance w(T) = sigma(T)^2 T linearly between pillars,
    from w(0) = 0, with flat-vol extrapolation past the last pillar. Same
    convention as QuantLib's ``BlackVarianceCurve``. The forward variance
    between two dates, w(t2) - w(t1), is what the path simulator consumes.
    """
    tenors: np.ndarray
    vols: np.ndarray

    def __post_init__(self):
        t = np.asarray(self.tenors, dtype=float)
        v = np.asarray(self.vols, dtype=float)
        if np.any(np.diff(t) <= 0) or t[0] <= 0 or np.any(v <= 0):
            raise ValueError("bad vol term structure")
        w = v * v * t
        if np.any(np.diff(w) < -1e-14):
            raise ValueError("total variance must be non-decreasing (calendar arbitrage)")
        object.__setattr__(self, "tenors", t)
        object.__setattr__(self, "vols", v)

    @classmethod
    def flat(cls, vol: float) -> "VolTermStructure":
        return cls(np.array([1.0]), np.array([vol]))

    def total_var(self, T):
        T = np.asarray(T, dtype=float)
        w_nodes = self.vols ** 2 * self.tenors
        inner = np.interp(T, np.concatenate([[0.0], self.tenors]), np.concatenate([[0.0], w_nodes]))
        return np.where(T > self.tenors[-1], self.vols[-1] ** 2 * T, inner)

    def vol(self, T):
        T = np.asarray(T, dtype=float)
        return np.sqrt(self.total_var(T) / np.maximum(T, 1e-12))

    def shifted(self, dvol: float) -> "VolTermStructure":
        return VolTermStructure(self.tenors, self.vols + dvol)


@dataclass(frozen=True)
class Market:
    spot: float
    curve: DiscountCurve          # risk-free discounting (INR sovereign / OIS)
    div: DiscountCurve            # continuous dividend (or implied carry) yield curve
    vol: VolTermStructure

    @classmethod
    def flat(cls, spot, r, q, sigma) -> "Market":
        return cls(spot, DiscountCurve.flat(r), DiscountCurve.flat(q), VolTermStructure.flat(sigma))

    def forward(self, T):
        return self.spot * self.div.df(T) / self.curve.df(T)

    def with_spot(self, spot):
        return replace(self, spot=float(spot))

    def with_vol_shift(self, dvol):
        return replace(self, vol=self.vol.shifted(dvol))

    def with_rate_shift(self, bp):
        """Parallel shift in the risk-free curve, holding the dividend curve fixed."""
        return replace(self, curve=self.curve.shifted(bp))
