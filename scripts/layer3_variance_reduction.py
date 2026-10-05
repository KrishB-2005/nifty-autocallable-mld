"""Layer 3a: variance reduction on the autocallable (daily knock-in).

Compares, at equal path counts and then at equal compute time:
  plain MC | antithetic | control variate = the ATM vanilla call |
  antithetic + vanilla controls (call, autocall digitals, puts) |
  antithetic + event controls (the note's own path events, priced exactly
  with multivariate normals in mld/analytic.py)

The vanilla call alone is a weak control for this note: it pays only in the
up-and-not-called states, while the note's value is driven by early-call
events and the downside put. Single-date digitals help, but "called in year 2"
also requires "not called in year 1", which no single-date option sees. The
event controls price those joint events directly, so the only payoff left to
simulate is the daily-barrier part: paths that touch 70% and then recover.
"""
import time

import numpy as np
import pandas as pd

from _common import AQUA, BLUE, INK2, ORANGE, SPEC, SPREAD, YELLOW, df_to_md, plt, save, write_md
from mld.autocall import evaluate, simulate_for
from mld.calibration import calibrate

m = calibrate().market
Ns = [4_000, 16_000, 64_000, 256_000]
METHODS = [  # label, antithetic, control, colour, marker
    ("Plain MC", False, None, INK2, "o"),
    ("Antithetic", True, None, YELLOW, "v"),
    ("CV: ATM call", False, "call", ORANGE, "s"),
    ("Antithetic + vanilla CVs", True, "full", AQUA, "D"),
    ("Antithetic + event CVs", True, "events", BLUE, "^"),
]

rows = []
for N in Ns:
    sims = {}
    for anti in (False, True):
        t = time.perf_counter()
        ps = simulate_for(SPEC, m, N, seed=N + anti, antithetic=anti)
        sims[anti] = (ps, time.perf_counter() - t)
    for label, anti, ctrl, *_ in METHODS:
        ps, t_sim = sims[anti]
        t = time.perf_counter()
        r = evaluate(SPEC, ps, m, credit_spread=SPREAD, control=ctrl)
        rows.append(dict(method=label, N=N, price=r.price.value, se=r.price.stderr,
                         seconds=t_sim + time.perf_counter() - t))
df = pd.DataFrame(rows)

fig, ax = plt.subplots(figsize=(6.6, 4.4))
for label, _, _, color, marker in METHODS:
    d = df[df.method == label]
    ax.loglog(d.N, d.se * 100, marker=marker, color=color, label=label)
plain = df[df.method == "Plain MC"]
ax.loglog(Ns, plain.se.iloc[0] * 100 * np.sqrt(Ns[0] / np.array(Ns)), ":", color=INK2, lw=1.5,
          label=r"$1/\sqrt{N}$ reference")
ax.set_xlabel("Paths N")
ax.set_ylabel("Standard error, bp of notional")
ax.set_title("Variance reduction on the NIFTY autocallable")
ax.legend(fontsize=8.5)
save(fig, "layer3_variance_reduction.png")

big = df[df.N == Ns[-1]].set_index("method")
base_var, base_t = big.loc["Plain MC", "se"] ** 2, big.loc["Plain MC", "seconds"]
table = pd.DataFrame({
    "Method": big.index,
    "Price": big.price.values,
    "SE (bp)": big.se.values * 100,
    "Variance reduction (x)": base_var / big.se.values ** 2,
    "Seconds": big.seconds.values,
    "Gain at equal time (x)": base_var * base_t / (big.se.values ** 2 * big.seconds.values),
})
slopes = {lbl: np.polyfit(np.log(df[df.method == lbl].N), np.log(df[df.method == lbl].se), 1)[0]
          for lbl, *_ in METHODS}
write_md("layer3_variance_reduction.md", f"""
## Layer 3a: variance reduction ({Ns[-1]:,} paths, base-case note)

{df_to_md(table, ".3f")}

"Variance reduction" is plain-MC variance over method variance at the same N. "Gain at equal time"
also divides by run time, which is the number that matters when choosing a method.
Fitted log-log slopes of SE vs N (theory -0.5): {", ".join(f"{k}: {v:.3f}" for k, v in slopes.items())}.
""")
