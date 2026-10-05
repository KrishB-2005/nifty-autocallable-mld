"""Calibrate forwards and an implied-vol term structure from one day's NSE
NIFTY option chain.

Steps
1. Forwards. For each expiry, put-call parity on strikes where both the call
   and the put traded: F = K + (C - P) / D(T), median over near-the-money
   strikes. Where a NIFTY future exists for the expiry its price is used
   instead (it is the more liquid instrument). Box spreads would also give
   D(T), but option closes on NSE are asynchronous enough that box-implied
   rates are noise (they range from -23% to +35% on this file), so D(T) comes
   from the rate curve and only F is taken from the market.
2. Implied vols. Black-76 on out-of-the-money options that actually traded
   (puts below F, calls above). Untraded strikes carry NSE's theoretical
   settlement prices and are dropped. Expiries under 7 days are dropped.
3. Smile. Per expiry, a quadratic in log-moneyness k = ln(K/F) over |k| <= 0.3:
   sigma(k) = a + b k + c k^2. Few long-dated strikes trade, so anything with
   more parameters overfits. `a` is the ATM-forward vol.
4. Term structure. ATM vols from expiries with enough strikes on both sides
   of the money, pruned so total variance increases with T.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .bs import implied_vol
from .curve import DiscountCurve
from .market import Market, VolTermStructure

DATA = Path(__file__).resolve().parent.parent / "data"


def load_curve(path=DATA / "inr_zero_curve.csv") -> DiscountCurve:
    c = pd.read_csv(path, comment="#")
    return DiscountCurve(c.tenor.values, c.zero_rate.values)


@dataclass
class Chain:
    trade_date: pd.Timestamp
    spot: float
    options: pd.DataFrame      # traded options: expiry, T, K, kind, price, volume
    futures: pd.DataFrame      # expiry, T, price


def load_chain(path=DATA / "nifty_fo_20261001.csv", min_days: int = 7) -> Chain:
    df = pd.read_csv(path, parse_dates=["TradDt", "XpryDt"])
    td = df.TradDt.iloc[0]
    spot = float(df.UndrlygPric.iloc[0])
    df["T"] = (df.XpryDt - td).dt.days / 365.0
    fut = df[df.FinInstrmTp == "IDF"].rename(columns={"XpryDt": "expiry", "ClsPric": "price"})
    opt = df[(df.FinInstrmTp == "IDO") & (df.TtlTradgVol > 0) & ((df.XpryDt - td).dt.days >= min_days)]
    opt = opt.rename(columns={"XpryDt": "expiry", "StrkPric": "K", "ClsPric": "price", "TtlTradgVol": "volume"})
    opt = opt.assign(kind=np.where(opt.OptnTp == "CE", "call", "put"))
    return Chain(td, spot, opt[["expiry", "T", "K", "kind", "price", "volume"]].reset_index(drop=True),
                 fut[["expiry", "T", "price"]].reset_index(drop=True))


def implied_forwards(chain: Chain, curve: DiscountCurve, band: float = 0.10) -> pd.DataFrame:
    rows = []
    futs = dict(zip(chain.futures.expiry, chain.futures.price))
    for exp, g in chain.options.groupby("expiry"):
        T = float(g["T"].iloc[0])
        D = float(curve.df(T))
        c = g[g.kind == "call"].set_index("K").price
        p = g[g.kind == "put"].set_index("K").price
        ks = c.index.intersection(p.index)
        near = ks[np.abs(ks / chain.spot - 1) <= band]
        ks = near if len(near) else ks
        f_pcp = float(np.median(ks + (c[ks] - p[ks]) / D)) if len(ks) else np.nan
        f_fut = futs.get(exp, np.nan)
        F, src = (f_fut, "future") if np.isfinite(f_fut) else (f_pcp, "put-call parity")
        rows.append(dict(expiry=exp, T=T, F=F, source=src, F_pcp=f_pcp, F_future=f_fut, n_pairs=len(ks)))
    out = pd.DataFrame(rows).dropna(subset=["F"])
    out["carry"] = np.log(out.F / chain.spot) / out["T"]
    out["r"] = curve.zero(out["T"].values)
    out["q_implied"] = out.r - out.carry
    return out.reset_index(drop=True)


def implied_vols(chain: Chain, fwd: pd.DataFrame, curve: DiscountCurve, min_price: float = 0.5) -> pd.DataFrame:
    F_of = dict(zip(fwd.expiry, fwd.F))
    rows = []
    for r in chain.options.itertuples():
        F = F_of.get(r.expiry)
        if F is None or r.price < min_price:
            continue
        otm = (r.kind == "put" and r.K < F) or (r.kind == "call" and r.K >= F)
        if not otm:
            continue
        D = float(curve.df(r.T))
        iv = implied_vol(r.price, F, r.K, r.T, D, r.kind)
        if np.isfinite(iv):
            rows.append(dict(expiry=r.expiry, T=r.T, K=r.K, kind=r.kind, price=r.price,
                             volume=r.volume, F=F, k=np.log(r.K / F), iv=iv))
    return pd.DataFrame(rows)


def fit_smiles(ivs: pd.DataFrame, min_points: int = 5, k_limit: float = 0.30) -> pd.DataFrame:
    """Quadratic smile per expiry, fitted on |k| <= k_limit. Deep wings (the
    Dec expiry trades strikes down to k = -0.64) would otherwise bend the fit
    away from the money, which is what the term structure uses."""
    rows = []
    for exp, g in ivs[np.abs(ivs.k) <= k_limit].groupby("expiry"):
        if len(g) < min_points:
            continue
        A = np.column_stack([np.ones(len(g)), g.k, g.k ** 2])
        coef, *_ = np.linalg.lstsq(A, g.iv.values, rcond=None)
        resid = g.iv.values - A @ coef
        rows.append(dict(expiry=exp, T=float(g["T"].iloc[0]), atm_vol=coef[0], skew=coef[1], curvature=coef[2],
                         n=len(g), k_min=g.k.min(), k_max=g.k.max(), rmse=np.sqrt(np.mean(resid ** 2))))
    return pd.DataFrame(rows)


def smile_vol(row, k):
    return row.atm_vol + row.skew * k + row.curvature * k ** 2


def atm_term_structure(smiles: pd.DataFrame, k_cover: float = 0.03) -> VolTermStructure:
    """ATM vol pillars from smiles whose quotes straddle the money, keeping only
    pillars that extend total variance (no calendar arbitrage)."""
    ok = smiles[(smiles.k_min <= -k_cover) & (smiles.k_max >= k_cover)].sort_values("T")
    tenors, vols, w_prev = [], [], 0.0
    for r in ok.itertuples():
        w = r.atm_vol ** 2 * r.T
        if w > w_prev:
            tenors.append(r.T)
            vols.append(r.atm_vol)
            w_prev = w
    return VolTermStructure(np.array(tenors), np.array(vols))


def carry_curve(fwd: pd.DataFrame, curve: DiscountCurve) -> DiscountCurve:
    """Dividend-yield curve q(T) that reproduces the market forwards on the
    given rate curve: F = S exp((r - q) T). It can come out negative because
    NIFTY forwards trade rich to G-secs."""
    f = fwd.sort_values("T")
    return DiscountCurve(f["T"].values, f.q_implied.values)


@dataclass
class Calibration:
    chain: Chain
    curve: DiscountCurve
    forwards: pd.DataFrame
    ivs: pd.DataFrame
    smiles: pd.DataFrame
    market: Market


def calibrate(chain_path=DATA / "nifty_fo_20261001.csv", curve_path=DATA / "inr_zero_curve.csv") -> Calibration:
    chain = load_chain(chain_path)
    curve = load_curve(curve_path)
    fwd = implied_forwards(chain, curve)
    ivs = implied_vols(chain, fwd, curve)
    smiles = fit_smiles(ivs)
    market = Market(chain.spot, curve, carry_curve(fwd, curve), atm_term_structure(smiles))
    return Calibration(chain, curve, fwd, ivs, smiles, market)
