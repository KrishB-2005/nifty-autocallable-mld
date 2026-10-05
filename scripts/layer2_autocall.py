"""Layer 2: price the autocallable on the calibrated 1 Oct 2026 market.

Outputs the note value split into bond leg and derivative overlay, how the
note ends (called in year 1/2/3, par, or loss), the coupon a desk could offer
at a 2% structuring margin, and the effect of daily vs final-only barrier
monitoring.
"""
from dataclasses import replace

import numpy as np
import pandas as pd

from _common import AQUA, BLUE, INK, ORANGE, SPEC, SPREAD, df_to_md, plt, save, write_md
from mld.autocall import evaluate, fair_coupon, path_pv, simulate_for
from mld.calibration import calibrate

N = 400_000
m = calibrate().market
ps = simulate_for(SPEC, m, N, seed=11, antithetic=True)
res = evaluate(SPEC, ps, m, credit_spread=SPREAD, control="events")
pv, principal, cyears, k_pay, knocked = path_pv(SPEC, ps, m, credit_spread=SPREAD)

loss = principal < SPEC.notional - 1e-12
outcomes = {
    "Called yr 1 (109)": np.mean((cyears > 0) & (k_pay == 0)),
    "Called yr 2 (118)": np.mean((cyears > 0) & (k_pay == 1)),
    "Coupon at yr 3 (127)": np.mean((cyears > 0) & (k_pay == 2)),
    "Par at yr 3 (100)": np.mean((cyears == 0) & ~loss),
    "Loss at yr 3 (<100)": np.mean(loss),
}
avg_loss_redemption = principal[loss].mean() if loss.any() else np.nan

fig, ax = plt.subplots(figsize=(6.6, 3.6))
names, probs = list(outcomes), np.array(list(outcomes.values()))
colors = [BLUE, BLUE, BLUE, AQUA, ORANGE]
bars = ax.barh(names[::-1], probs[::-1] * 100, color=colors[::-1], height=0.6)
for b, p in zip(bars, probs[::-1]):
    ax.text(b.get_width() + 0.8, b.get_y() + b.get_height() / 2, f"{p:.1%}", va="center", color=INK)
ax.set_xlabel("Risk-neutral probability, %")
ax.set_xlim(0, max(probs) * 100 + 10)
ax.grid(axis="y", visible=False)
ax.set_title("How the 3y NIFTY autocallable ends (calibrated market)")
save(fig, "layer2_outcomes.png")

c_fair = fair_coupon(SPEC, m, 98.0, N, seed=11, credit_spread=SPREAD)
c_par = fair_coupon(SPEC, m, 100.0, N, seed=11, credit_spread=SPREAD)

# Monitoring convention: daily closes vs final fixing only
eur = replace(SPEC, ki_daily=False)
r_eur = evaluate(eur, simulate_for(eur, m, N, seed=11, antithetic=True), m, credit_spread=SPREAD, control="events")
mon = pd.DataFrame([
    dict(barrier="Daily closes (base)", price=res.price.value, prob_ki=res.prob_ki, prob_loss=res.prob_loss),
    dict(barrier="Final fixing only", price=r_eur.price.value, prob_ki=r_eur.prob_ki, prob_loss=r_eur.prob_loss),
])

write_md("layer2.md", f"""
## Layer 2: base-case note on the 1 Oct 2026 market

Term sheet: 3y on NIFTY 50, initial fixing {m.spot:,.2f}, annual observations, autocall at 100%,
{SPEC.coupon_rate:.0%} p.a. snowball coupon, 70% knock-in on daily closes, issuer spread {SPREAD*1e4:.0f}bp.
{N:,} paths, antithetic with event control variates (mld/analytic.py).

| Item | Value (per 100) |
|---|---|
| Note fair value | {res.price.value:.4f} +/- {res.price.stderr:.4f} |
| Zero-coupon bond leg (100 at 3y, issuer curve) | {res.zcb:.4f} |
| Derivative overlay (note minus bond) | {res.overlay:+.4f} |
| Structuring margin at issue price 100 | {100 - res.price.value:.4f} |
| Expected life | {res.expected_life:.2f} years |
| Probability the barrier is touched while the note is alive | {res.prob_ki:.2%} |
| Probability of capital loss | {res.prob_loss:.2%} |
| Average redemption when there is a loss | {avg_loss_redemption:.2f} |
| Coupon for a 98.00 fair value (2% margin) | {c_fair:.4%} p.a. |
| Coupon for a 100.00 fair value (no margin) | {c_par:.4%} p.a. |

Outcome probabilities:

{df_to_md(pd.DataFrame({"Outcome": names, "Probability": probs}), ".4f")}

Barrier monitoring convention:

{df_to_md(mon, ".4f")}
""")
