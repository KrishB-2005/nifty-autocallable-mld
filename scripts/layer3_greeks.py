"""Layer 3b: Greeks.

1. Vanilla 3y ATM call: pathwise and likelihood-ratio MC estimators against
   the closed form.
2. The note, with each estimator against a benchmark: for the final-fixing
   barrier, bumping the semi-analytic price (mld/analytic.py) is exact up to
   the bump; for the daily barrier there is no closed form, so FD with common
   random numbers is the reference and LR is shown to see how it degrades.
   Run on a flat-vol market so "vega" means the same thing for every
   estimator (the LR score is for a parallel shift of step vols).
3. Delta and vega of the daily-barrier note across spot, on the calibrated
   market: the risk profile a desk would hedge.
"""
from dataclasses import replace

import numpy as np
import pandas as pd

from _common import BLUE, INK2, ORANGE, SPEC, SPREAD, df_to_md, plt, save, write_md
from mld.analytic import european_barrier_price
from mld.autocall import path_pv, simulate_for
from mld.calibration import calibrate
from mld.greeks import fd_greeks, lr_greeks
from mld.market import Market
from mld.vanilla import closed_form, mc_european

cal = calibrate().market
S, T = cal.spot, SPEC.maturity
flat = Market.flat(S, float(cal.curve.zero(T)), float(cal.div.zero(T)), float(cal.vol.vol(T)))
N = 400_000

# 1. vanilla call: benchmark by bumping the closed form
h, dv = 1e-4 * S, 1e-5
cf_delta = (closed_form(flat.with_spot(S + h), S, T) - closed_form(flat.with_spot(S - h), S, T)) / (2 * h)
cf_vega = (closed_form(flat.with_vol_shift(dv), S, T) - closed_form(flat.with_vol_shift(-dv), S, T)) / (2 * dv) * 0.01
v = mc_european(flat, S, T, N, seed=1, antithetic=True)
vanilla = pd.DataFrame([
    dict(greek="Delta", closed_form=cf_delta, pathwise=v["delta_pw"].value, pathwise_se=v["delta_pw"].stderr,
         lr=v["delta_lr"].value, lr_se=v["delta_lr"].stderr),
    dict(greek="Vega (per vol pt)", closed_form=cf_vega, pathwise=v["vega_pw"].value * 0.01,
         pathwise_se=v["vega_pw"].stderr * 0.01, lr=v["vega_lr"].value * 0.01, lr_se=v["vega_lr"].stderr * 0.01),
])

# 2. the note: delta per 1% spot move and vega per vol point, per 100 notional
eur = replace(SPEC, ki_daily=False)
hb, vb = 0.01, 0.01
ana_delta = (european_barrier_price(eur, flat.with_spot(S * (1 + hb)), S, SPREAD)
             - european_barrier_price(eur, flat.with_spot(S * (1 - hb)), S, SPREAD)) / 2
ana_vega = (european_barrier_price(eur, flat.with_vol_shift(vb), S, SPREAD)
            - european_barrier_price(eur, flat.with_vol_shift(-vb), S, SPREAD)) / 2

rows = []
for label, spec, bench in [("Final-fixing barrier", eur, (ana_delta, ana_vega)), ("Daily barrier", SPEC, None)]:
    fd = fd_greeks(spec, flat, N, seed=3, credit_spread=SPREAD)
    lr = lr_greeks(spec, flat, N, seed=4, credit_spread=SPREAD)
    d1 = S * 0.01
    est = [("FD with CRN", fd.delta.value * d1, fd.delta.stderr * d1, fd.vega.value, fd.vega.stderr),
           ("Likelihood ratio", lr["delta"].value * d1, lr["delta"].stderr * d1, lr["vega"].value, lr["vega"].stderr)]
    if bench:
        est.insert(0, ("Semi-analytic (bumped)", bench[0], 0.0, bench[1], 0.0))
    for name, d, dse, vg, vse in est:
        rows.append(dict(note=label, estimator=name, delta_1pct=d, delta_se=dse, vega_1pt=vg, vega_se=vse))
note = pd.DataFrame(rows)

# FD-CRN against the exact benchmark over more seeds, to separate bias from luck
zs = []
for seed in range(10, 18):
    g = fd_greeks(eur, flat, N, seed=seed, credit_spread=SPREAD)
    zs.append(((g.delta.value * S * 0.01 - ana_delta) / (g.delta.stderr * S * 0.01),
               (g.vega.value - ana_vega) / g.vega.stderr))
zs = np.array(zs)

# 3. risk profile across spot on the calibrated market (FD with CRN)
levels = np.round(np.arange(0.60, 1.301, 0.025), 3)
Np = 200_000
ps0 = simulate_for(SPEC, cal, Np, seed=9, antithetic=True)
psu = simulate_for(SPEC, cal.with_vol_shift(vb), Np, seed=9, antithetic=True)
psd = simulate_for(SPEC, cal.with_vol_shift(-vb), Np, seed=9, antithetic=True)
pv = lambda m, p: path_pv(SPEC, p, m, S, SPREAD)[0].mean()
prof = []
for x in levels:
    mx = cal.with_spot(S * x)
    delta = (pv(cal.with_spot(S * x * 1.01), ps0) - pv(cal.with_spot(S * x * 0.99), ps0)) / 2  # per 1% move
    vega = (pv(mx.with_vol_shift(vb), psu) - pv(mx.with_vol_shift(-vb), psd)) / 2
    prof.append(dict(level=x, price=pv(mx, ps0), delta=delta, vega=vega))
prof = pd.DataFrame(prof)

fig, axes = plt.subplots(1, 2, figsize=(10, 3.9), sharex=True)
for ax, col, color, title in [(axes[0], "delta", BLUE, "Delta: value change per 1% NIFTY move"),
                              (axes[1], "vega", ORANGE, "Vega: value change per +1 vol point")]:
    ax.plot(prof.level * 100, prof[col], color=color)
    ax.axvline(70, color=INK2, ls=":", lw=1.2)
    ax.axvline(100, color=INK2, ls=":", lw=1.2)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_title(title)
    ax.set_xlabel("NIFTY, % of initial fixing")
    ax.set_ylabel("Per 100 notional")
axes[0].annotate("knock-in 70%", (70, axes[0].get_ylim()[1]), xytext=(3, -12), textcoords="offset points",
                 color=INK2, fontsize=8.5)
axes[0].annotate("autocall 100%", (100, axes[0].get_ylim()[1]), xytext=(3, -12), textcoords="offset points",
                 color=INK2, fontsize=8.5)
save(fig, "layer3_greeks_profile.png")

write_md("layer3_greeks.md", f"""
## Layer 3b: Greeks

Flat market for the estimator comparison: spot {S:,.2f}, r = {flat.curve.zero_rates[0]:.4%},
q = {flat.div.zero_rates[0]:.4%}, vol = {flat.vol.vols[0]:.4%} (the calibrated 3y values). {N:,} paths.

### Vanilla 3y ATM call

{df_to_md(vanilla, ".4f")}

### The note (per 100 notional; delta per 1% spot move, vega per vol point)

{df_to_md(note, ".4f")}

On the coarse final-fixing grid the LR estimator is unbiased and usable. On the daily grid its
delta score is Z_1 / (sigma sqrt(dt_1)) with dt_1 = 1/252, and its vega score sums 756 terms, so
its standard error is many times FD-CRN's. The payoff jumps at every trigger, so pathwise
derivatives are not available for the note at all.

FD-CRN vs the semi-analytic Greeks over 8 further seeds: z-scores average {zs[:, 0].mean():+.2f} (delta)
and {zs[:, 1].mean():+.2f} (vega) with standard deviations {zs[:, 0].std():.2f} and {zs[:, 1].std():.2f},
so the table's single-seed gaps are noise, not bias.

### Risk profile across spot (calibrated market, daily barrier, FD with CRN)

{df_to_md(prof.rename(columns={"level": "spot / S_ref"}), ".4f")}
""")
