"""Layer 1: bond leg, Black-Scholes call, and MC convergence to it.

For each path count N, 25 independent MC runs of the 3y ATM call are compared
with the closed form. The RMS error across runs should fall as 1/sqrt(N) and
sit on top of the average reported standard error; if it sat above, the MC
would be biased.
"""
import numpy as np
import pandas as pd

from _common import BLUE, INK2, ORANGE, SPEC, SPREAD, df_to_md, plt, save, write_md
from mld.calibration import calibrate
from mld.curve import zero_coupon_bond
from mld.vanilla import closed_form, mc_european

m = calibrate().market
S, T = m.spot, SPEC.maturity
bs = closed_form(m, S, T, "call")

Ns = [1_000, 4_000, 16_000, 64_000, 256_000, 1_024_000]
runs = 25
rows = []
for N in Ns:
    est = [mc_european(m, S, T, N, seed=1000 * N + i)["price"] for i in range(runs)]
    err = np.array([e.value - bs for e in est])
    rows.append(dict(N=N, rmse=np.sqrt(np.mean(err ** 2)), mean_se=np.mean([e.stderr for e in est]),
                     bias=err.mean(), bias_se=err.std(ddof=1) / np.sqrt(runs)))
df = pd.DataFrame(rows)

fig, ax = plt.subplots(figsize=(6.4, 4.2))
ax.loglog(df.N, df.rmse / bs * 1e4, "o-", color=BLUE, label="RMS error vs Black-Scholes (25 runs)")
ax.loglog(df.N, df.mean_se / bs * 1e4, "s--", color=ORANGE, label="Reported standard error")
ref = df.rmse.iloc[0] / bs * 1e4 * np.sqrt(Ns[0] / np.array(Ns))
ax.loglog(Ns, ref, ":", color=INK2, label=r"$1/\sqrt{N}$ reference")
ax.set_xlabel("Paths N")
ax.set_ylabel("Error, bp of option price")
ax.set_title("MC price of 3y ATM NIFTY call converges to Black-Scholes")
ax.legend()
save(fig, "layer1_convergence.png")

slope = np.polyfit(np.log(df.N), np.log(df.rmse), 1)[0]
big = mc_european(m, S, T, 2_000_000, seed=7, antithetic=True)["price"]
zcb = zero_coupon_bond(m.curve, T, 100.0, SPREAD)
zcb_rf = zero_coupon_bond(m.curve, T, 100.0)
show = pd.DataFrame({"Paths N": [f"{n:,}" for n in df.N], "RMS error (bp)": df.rmse / bs * 1e4,
                     "Mean reported SE (bp)": df.mean_se / bs * 1e4})
write_md("layer1.md", f"""
## Layer 1: bond leg and vanilla anchor (market of {m.spot:,.2f}, 1 Oct 2026)

| Item | Value |
|---|---|
| ZCB, 100 face, {T:.0f}y, risk-free curve | {zcb_rf:.4f} |
| ZCB, 100 face, {T:.0f}y, curve + {SPREAD*1e4:.0f}bp issuer spread | {zcb:.4f} |
| 3y forward | {m.forward(T):,.2f} |
| 3y ATM vol (calibrated) | {float(m.vol.vol(T)):.4f} |
| ATM call, Black-Scholes | {bs:.4f} |
| ATM call, MC 2,000,000 antithetic | {big.value:.4f} +/- {big.stderr:.4f} ({(big.value - bs) / big.stderr:+.2f} SE) |
| Fitted log-log slope of RMS error vs N | {slope:.3f} (theory: -0.5) |

{df_to_md(show, ".2f")}
""")
