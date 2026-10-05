"""Validate this pricer against QuantLib, component by component.

QuantLib is used only as an independent benchmark here; nothing in `mld/`
imports it. Every row compares our number with QuantLib's on identical
inputs and reports the gap in basis points, next to the Monte Carlo
standard error where one applies.

    python validation/quantlib_check.py            # writes results/validation.md
"""
from __future__ import annotations

import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import QuantLib as ql

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mld.autocall import AutocallSpec, PathSummary, evaluate, price  # noqa: E402
from mld.bs import black_asset_or_nothing, black_digital  # noqa: E402
from mld.calibration import calibrate  # noqa: E402
from mld.curve import DiscountCurve, zero_coupon_bond  # noqa: E402
from mld.market import Market, VolTermStructure  # noqa: E402
from mld.paths import make_grid, simulate  # noqa: E402
from mld.vanilla import closed_form, mc_european  # noqa: E402

TODAY = ql.Date(1, 10, 2026)
DC = ql.Actual365Fixed()
ql.Settings.instance().evaluationDate = TODAY
N_OURS = 400_000
N_QL = 60_000


# ---------------------------------------------------------------- QuantLib side
def days(t):
    return int(round(t * 365))


def on_day_grid(c: DiscountCurve) -> DiscountCurve:
    """Snap curve pillars to whole days so both libraries see identical nodes."""
    return DiscountCurve(np.array([days(t) / 365 for t in c.tenors]), c.zero_rates)


def ql_curve(c: DiscountCurve):
    dates = [TODAY] + [TODAY + days(t) for t in c.tenors]
    dfs = [1.0] + list(c.df(c.tenors))
    curve = ql.DiscountCurve(dates, dfs, DC)
    curve.enableExtrapolation()
    return ql.YieldTermStructureHandle(curve)


def ql_vol(v: VolTermStructure):
    if len(v.tenors) == 1:
        return ql.BlackVolTermStructureHandle(ql.BlackConstantVol(TODAY, ql.NullCalendar(), float(v.vols[0]), DC))
    dates = [TODAY + days(t) for t in v.tenors]
    surf = ql.BlackVarianceCurve(TODAY, dates, list(v.vols), DC, False)
    surf.enableExtrapolation()
    return ql.BlackVolTermStructureHandle(surf)


def ql_process(m: Market):
    return ql.BlackScholesMertonProcess(ql.QuoteHandle(ql.SimpleQuote(m.spot)),
                                        ql_curve(m.div), ql_curve(m.curve), ql_vol(m.vol))


def ql_european(m: Market, payoff, T):
    opt = ql.VanillaOption(payoff, ql.EuropeanExercise(TODAY + days(T)))
    opt.setPricingEngine(ql.AnalyticEuropeanEngine(ql_process(m)))
    return opt.NPV()


def ql_barrier(m: Market, K, B, T, engine, mc=False):
    opt = ql.BarrierOption(ql.Barrier.DownIn, B, 0.0, ql.PlainVanillaPayoff(ql.Option.Put, K),
                           ql.EuropeanExercise(TODAY + days(T)))
    opt.setPricingEngine(engine)
    return opt.NPV(), (opt.errorEstimate() if mc else 0.0)


def ql_paths(m: Market, obs_times, steps, n_pairs, seed=2026) -> PathSummary:
    """Autocall paths from QuantLib's own BSM process and path generator."""
    proc = ql_process(m)
    grid = ql.TimeGrid(list(obs_times), steps)
    t = np.array([grid[i] for i in range(len(grid))])
    obs_idx = [int(np.argmin(np.abs(t - x))) for x in obs_times]
    rsg = ql.GaussianRandomSequenceGenerator(
        ql.UniformRandomSequenceGenerator(steps, ql.UniformRandomGenerator(seed)))
    gen = ql.GaussianPathGenerator(proc, grid, rsg, False)
    plus, minus = [], []
    for _ in range(n_pairs):
        plus.append(np.fromiter(gen.next().value(), float, len(grid)))
        minus.append(np.fromiter(gen.antithetic().value(), float, len(grid)))
    s = np.vstack(plus + minus) / m.spot
    run_min = np.minimum.accumulate(s, axis=1)[:, obs_idx]
    return PathSummary(s[:, obs_idx], run_min, None, None, antithetic=True)


# ------------------------------------------------------------------- our side
def our_down_in_put(m: Market, K, B, T, n, seed=7):
    grid = make_grid([T], 252, daily=True)
    ps = simulate(m, grid, n, seed, antithetic=True, track_min=True)
    ST = m.spot * ps.rel_obs[:, 0]
    hit = m.spot * ps.rel_min[:, -1] <= B
    pv = m.curve.df(T) * np.where(hit, np.maximum(K - ST, 0.0), 0.0)
    y = ps.pair_mean(pv)
    return y.mean(), y.std(ddof=1) / np.sqrt(len(y))


# -------------------------------------------------------------------- checks
def row(group, item, ours, bench, unit_base, se=0.0, bench_se=0.0, unit="bp of price"):
    diff_bp = (ours - bench) / unit_base * 1e4
    se_bp = np.hypot(se, bench_se) / unit_base * 1e4
    z = abs(ours - bench) / np.hypot(se, bench_se) if se or bench_se else np.nan
    return dict(group=group, item=item, ours=ours, quantlib=bench, diff_bp=diff_bp,
                se_bp=se_bp if se or bench_se else np.nan, z=z, unit=unit)


def main():
    t0 = time.time()
    cal = calibrate()
    m = Market(cal.market.spot, on_day_grid(cal.market.curve), cal.market.div, cal.market.vol)
    S = m.spot
    rows = []

    # 1. Bond leg on the INR curve
    for T in (0.5, 1.0, 3.0, 4.5):
        T = days(T) / 365
        ours = zero_coupon_bond(m.curve, T, 100.0)
        bench = 100.0 * ql_curve(m.curve).discount(TODAY + days(T))
        rows.append(row("Bond leg", f"ZCB {T:.2f}y, 100 face", ours, bench, ours))

    # 2. Vanillas on the calibrated term structures: closed form and our MC vs QL analytic
    T = days(3.0) / 365
    for kind, K, label in [("call", S, "ATM call 3y"), ("put", 0.85 * S, "85% put 3y")]:
        ql_t = ql.Option.Call if kind == "call" else ql.Option.Put
        bench = ql_european(m, ql.PlainVanillaPayoff(ql_t, K), T)
        rows.append(row("Vanilla (calibrated mkt)", f"{label}, Black-Scholes", closed_form(m, K, T, kind), bench, bench))
        mc = mc_european(m, K, T, N_OURS, seed=1, kind=kind, antithetic=True)["price"]
        rows.append(row("Vanilla (calibrated mkt)", f"{label}, our MC {N_OURS:,}", mc.value, bench, bench, mc.stderr))

    # 3. Digitals that make up the autocall
    F, D, v = m.forward(T), m.curve.df(T), m.vol.vol(T)
    rows.append(row("Digitals", "Cash-or-nothing call @100%, 3y", float(black_digital(F, S, T, v, D)),
                    ql_european(m, ql.CashOrNothingPayoff(ql.Option.Call, S, 1.0), T), 1.0, unit="bp of 1 unit cash"))
    aon = float(black_asset_or_nothing(F, 0.7 * S, T, v, D, "put"))
    rows.append(row("Digitals", "Asset-or-nothing put @70%, 3y", aon,
                    ql_european(m, ql.AssetOrNothingPayoff(ql.Option.Put, 0.7 * S), T), aon))

    # 4. Knock-in put, flat market (QuantLib's barrier engines assume flat inputs)
    flat = Market.flat(S, float(m.curve.zero(T)), float(m.div.zero(T)), float(m.vol.vol(T)))
    proc = ql_process(flat)
    B, K, sig = 0.7 * S, S, float(flat.vol.vols[0])
    ours, se = our_down_in_put(flat, K, B, T, N_OURS)
    mc_ql, mc_ql_se = ql_barrier(flat, K, B, T, ql.MCBarrierEngine(
        proc, "pseudorandom", timeSteps=days(T) * 252 // 365, isBiased=True,
        requiredSamples=N_QL, seed=42), mc=True)
    bgk = B * np.exp(-0.5826 * sig * np.sqrt(1 / 252))
    cont_bgk, _ = ql_barrier(flat, K, bgk, T, ql.AnalyticBarrierEngine(proc))
    cont, _ = ql_barrier(flat, K, B, T, ql.AnalyticBarrierEngine(proc))
    rows.append(row("Down-and-in put 100/70, 3y", "vs QL MC, daily monitoring", ours, mc_ql, mc_ql, se, mc_ql_se))
    rows.append(row("Down-and-in put 100/70, 3y", "vs QL analytic, BGK-shifted barrier", ours, cont_bgk, cont_bgk, se))
    rows.append(row("Down-and-in put 100/70, 3y", "vs QL analytic, continuous (no shift)", ours, cont, cont, se))

    # 5. Single-observation note: exact decomposition from QuantLib digitals
    c, B1 = 0.09, 0.70
    spec1 = AutocallSpec(obs_times=(T,), coupon_rate=c, ki_barrier=B1, ki_daily=False)
    dig_ac = ql_european(m, ql.CashOrNothingPayoff(ql.Option.Call, S, 1.0), T)
    dig_b = ql_european(m, ql.CashOrNothingPayoff(ql.Option.Call, B1 * S, 1.0), T)
    aon_put = ql_european(m, ql.AssetOrNothingPayoff(ql.Option.Put, B1 * S), T)
    exact = 100 * (1 + c * T) * dig_ac + 100 * (dig_b - dig_ac) + 100 / S * aon_put
    r1 = price(spec1, m, N_OURS, seed=3, control="full")
    rows.append(row("Autocall, 1 observation", "our MC vs QL digital decomposition", r1.price.value, exact, 100.0,
                    r1.price.stderr, unit="bp of notional"))

    # 6. Full note: our engine vs our payoff on QuantLib-generated paths
    spec = replace(AutocallSpec(), obs_times=tuple(days(x) / 365 for x in (1, 2, 3)))
    ours = price(spec, m, N_OURS, seed=5, control="full", credit_spread=0.01)
    qps = ql_paths(m, spec.obs_times, 756, N_QL // 2)
    theirs = evaluate(spec, qps, m, credit_spread=0.01)
    rows.append(row("Autocall 3y, daily KI", "our paths vs QuantLib paths", ours.price.value, theirs.price.value,
                    100.0, ours.price.stderr, theirs.price.stderr, unit="bp of notional"))

    df = pd.DataFrame(rows)
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    md = ["| Check | Case | Ours | QuantLib | Diff (bp) | Combined MC SE (bp) | abs(z) | Unit |",
          "|---|---|---:|---:|---:|---:|---:|---|"]
    for r in df.itertuples():
        f = lambda x: "" if np.isnan(x) else f"{x:.2f}"
        md.append(f"| {r.group} | {r.item} | {r.ours:.6f} | {r.quantlib:.6f} | {r.diff_bp:+.2f} | "
                  f"{f(r.se_bp)} | {f(r.z)} | {r.unit} |")
    (out / "validation.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    print(f"\n{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
