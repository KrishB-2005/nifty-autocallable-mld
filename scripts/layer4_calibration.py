"""Layer 4: what the NSE option chain says, and how much the vol choice matters.

The pricer uses one deterministic vol per date (the ATM term structure).
The knock-in put, though, is struck far below the money: at 3y the 70%
barrier is around k = ln(0.7 S / F) = -0.67 because NIFTY forwards carry
about 6.5% a year. Equity smiles are steep there. The last table prices
the note with a flat vol read off the longest liquid smile at different
strikes, to show how far a skew-aware model could move the price.
"""
import numpy as np
import pandas as pd

from _common import BLUE, INK2, ORANGE, SPEC, SPREAD, df_to_md, plt, save, write_md
from mld.autocall import price
from mld.calibration import calibrate, smile_vol
from mld.market import Market, VolTermStructure

cal = calibrate()
m, S = cal.market, cal.chain.spot
T = SPEC.maturity

# smiles for four expiries
show = ["2026-10-27", "2026-12-29", "2027-12-28", "2028-12-26"]
fig, axes = plt.subplots(2, 2, figsize=(9.5, 6.4), sharey=True)
for ax, exp in zip(axes.ravel(), show):
    pts = cal.ivs[cal.ivs.expiry == pd.Timestamp(exp)]
    row = cal.smiles[cal.smiles.expiry == pd.Timestamp(exp)].iloc[0]
    kk = np.linspace(max(pts.k.min(), -0.3), min(pts.k.max(), 0.3), 100)
    inside = pts[np.abs(pts.k) <= 0.3]
    outside = pts[np.abs(pts.k) > 0.3]
    ax.scatter(inside.k, inside.iv * 100, s=18, color=BLUE, label="Traded OTM option")
    if len(outside):
        ax.scatter(outside.k, outside.iv * 100, s=18, facecolor="none", edgecolor=BLUE, label="Excluded from fit")
    ax.plot(kk, smile_vol(row, kk) * 100, color=ORANGE, label="Quadratic fit")
    ax.set_title(f"Expiry {exp}  (T = {row['T']:.2f}y, {int(row.n)} quotes)", fontsize=10)
    ax.set_xlabel("log-moneyness ln(K/F)")
    ax.set_ylabel("Implied vol, %")
axes[0, 0].legend(fontsize=8)
fig.suptitle("NIFTY implied vol smiles, NSE close 1 Oct 2026", x=0.02, ha="left", fontweight="bold")
save(fig, "layer4_smiles.png")

# term structure of ATM vol and implied carry
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
tt = np.linspace(0.02, 3.5, 200)
axes[0].plot(tt, m.vol.vol(tt) * 100, color=BLUE)
axes[0].scatter(m.vol.tenors, m.vol.vols * 100, color=BLUE, s=22, zorder=3)
axes[0].axvline(T, color=INK2, ls=":", lw=1.2)
axes[0].set_title("ATM implied vol term structure")
axes[0].set_xlabel("Years")
axes[0].set_ylabel("Vol, %")
fw = cal.forwards
axes[1].plot(fw["T"], fw.carry * 100, "o-", color=ORANGE, label="Implied carry ln(F/S)/T")
axes[1].plot(fw["T"], fw.r * 100, "s--", color=BLUE, label="INR zero rate (approx.)")
axes[1].set_title("Forward carry vs the rate curve")
axes[1].set_xlabel("Years")
axes[1].set_ylabel("% per year")
axes[1].legend(fontsize=8.5)
save(fig, "layer4_term_structure.png")

# skew sensitivity: flat vol read off the longest liquid smile at several strikes
last = cal.smiles.sort_values("T").iloc[-1]
F_last = cal.forwards.set_index("expiry").loc[last.expiry, "F"]
rows = []
N = 200_000
base = price(SPEC, m, N, seed=31, control="events", credit_spread=SPREAD).price
rows.append(dict(vol_input="Calibrated ATM term structure (base)", vol=float(m.vol.vol(T)), price=base.value,
                 diff_vs_base=0.0))
for pct in (1.00, 0.85, 0.70):
    k = np.log(pct * S / F_last)
    v = float(smile_vol(last, k))
    mk = Market(S, m.curve, m.div, VolTermStructure.flat(v))
    p = price(SPEC, mk, N, seed=31, control="events", credit_spread=SPREAD).price
    note = " (extrapolated, k < -0.3)" if k < -0.3 else ""
    rows.append(dict(vol_input=f"Flat, {last.expiry:%b-%Y} smile at K = {pct:.0%} of spot{note}", vol=v,
                     price=p.value, diff_vs_base=p.value - base.value))
skew = pd.DataFrame(rows)

fwd_tbl = fw.assign(expiry=fw.expiry.dt.strftime("%Y-%m-%d"))[
    ["expiry", "T", "F", "source", "n_pairs", "carry", "r", "q_implied"]]
smile_tbl = cal.smiles.assign(expiry=cal.smiles.expiry.dt.strftime("%Y-%m-%d"))[
    ["expiry", "T", "n", "atm_vol", "skew", "curvature", "rmse"]]
write_md("layer4_calibration.md", f"""
## Layer 4: calibration to the NSE option chain, 1 Oct 2026 (NIFTY {S:,.2f})

{len(cal.chain.options):,} traded NIFTY options with at least 7 days to expiry; {len(cal.ivs):,} OTM quotes gave an implied vol.

### Forwards

{df_to_md(fwd_tbl, ".4f")}

NIFTY forwards imply about 6.5% carry, at or above the INR zero curve, so the implied dividend yield is
slightly negative. Index futures in India usually trade rich to G-secs. The pricer takes forwards
from the market, since futures are the hedge, and discounts on the rate curve.

### Smiles (quadratic in k = ln(K/F), fitted on |k| <= 0.3)

{df_to_md(smile_tbl, ".4f")}

### How much the vol input matters for this note

{df_to_md(skew, ".4f")}

The knock-in sits deep in the put wing, where implied vol is well above ATM, so an ATM-vol model
overvalues the note to the investor. A local or stochastic vol model calibrated to the whole smile
is the fix; see "What breaks this model" in the README.
""")
