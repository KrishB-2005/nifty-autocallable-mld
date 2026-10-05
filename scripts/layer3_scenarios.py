"""Layer 3c: scenario grid and stress tests on the calibrated market.

Instantaneous shocks just after issue: the initial fixing stays at
22,421.95 and spot, vol, rates and the issuer spread move.
"""
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from _common import AQUA, BLUE, INK, INK2, ORANGE, SPEC, SPREAD, YELLOW, df_to_md, plt, save, write_md
from mld.calibration import calibrate
from mld.scenarios import spot_vol_grid, stress_table

m = calibrate().market
base_vol = float(m.vol.vol(SPEC.maturity))
spots = np.round(np.arange(0.60, 1.301, 0.05), 2)
shifts = np.round(np.arange(-0.05, 0.1501, 0.025), 3)
N = 100_000

grid = spot_vol_grid(SPEC, m, spots, shifts, n_paths=N, seed=21, credit_spread=SPREAD)

# sequential single-hue ramp (light = low value)
ramp = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
cmap = LinearSegmentedColormap.from_list("seq_blue", ramp[::-1])  # dark = low value: losses stand out

fig, ax = plt.subplots(figsize=(10, 4.8))
im = ax.imshow(grid.values, cmap=cmap, aspect="auto", origin="lower",
               vmin=grid.values.min(), vmax=grid.values.max())
ax.set_xticks(range(len(spots)), [f"{x:.0%}" for x in spots])
ax.set_yticks(range(len(shifts)), [f"{base_vol + s:.1%}" for s in shifts])
ax.set_xlabel("NIFTY, % of initial fixing")
ax.set_ylabel("3y implied vol (parallel shift)")
ax.grid(False)
mid = 0.5 * (grid.values.min() + grid.values.max())
for i in range(len(shifts)):
    for j in range(len(spots)):
        val = grid.values[i, j]
        ax.text(j, i, f"{val:.1f}", ha="center", va="center", fontsize=7.5,
                color="white" if val < mid else INK)
base_i = int(np.argmin(np.abs(shifts)))
base_j = int(np.argmin(np.abs(spots - 1.0)))
ax.add_patch(plt.Rectangle((base_j - 0.5, base_i - 0.5), 1, 1, fill=False, ec=ORANGE, lw=2))
cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
cb.set_label("Note value per 100")
ax.set_title("Note value across spot and volatility (orange box = today)")
save(fig, "layer3_scenario_grid.png")

fig, ax = plt.subplots(figsize=(6.6, 4.2))
for s, color in zip([-0.025, 0.0, 0.05, 0.10], [BLUE, ORANGE, AQUA, YELLOW]):
    i = int(np.argmin(np.abs(shifts - s)))
    ax.plot(spots * 100, grid.values[i], color=color, marker="o", ms=4, label=f"vol {base_vol + s:.1%}")
ax.axvline(70, color=INK2, ls=":", lw=1.2)
ax.axhline(100, color=INK2, lw=0.8)
ax.set_xlabel("NIFTY, % of initial fixing")
ax.set_ylabel("Note value per 100")
ax.set_title("Note value vs spot at four vol levels")
ax.legend(loc="lower right")
save(fig, "layer3_scenario_lines.png")

stress = stress_table(SPEC, m, n_paths=N, seed=21, credit_spread=SPREAD)
grid_md = grid.copy()
grid_md.index = [f"{base_vol + s:.1%}" for s in shifts]
grid_md.columns = [f"{x:.0%}" for x in spots]
grid_md = grid_md.reset_index().rename(columns={"index": "vol \\ spot"})
write_md("layer3_scenarios.md", f"""
## Layer 3c: scenario analysis (calibrated market, {N:,} paths per vol level, common random numbers)

### Spot x vol grid (note value per 100)

{df_to_md(grid_md, ".2f")}

### Stress tests

{df_to_md(stress, ".3f")}

Spot shocks keep the initial fixing at {m.spot:,.2f}. "Rates" shifts the INR discount curve and,
through the forward, the index drift; the dividend curve is held fixed. "Issuer spread" moves
only the discounting of the note's cash flows.
""")
