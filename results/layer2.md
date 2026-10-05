## Layer 2: base-case note on the 1 Oct 2026 market

Term sheet: 3y on NIFTY 50, initial fixing 22,421.95, annual observations, autocall at 100%,
9% p.a. snowball coupon, 70% knock-in on daily closes, issuer spread 100bp.
400,000 paths, antithetic with event control variates (mld/analytic.py).

| Item | Value (per 100) |
|---|---|
| Note fair value | 98.3364 +/- 0.0037 |
| Zero-coupon bond leg (100 at 3y, issuer curve) | 79.9715 |
| Derivative overlay (note minus bond) | +18.3649 |
| Structuring margin at issue price 100 | 1.6636 |
| Expected life | 1.54 years |
| Probability the barrier is touched while the note is alive | 3.46% |
| Probability of capital loss | 3.34% |
| Average redemption when there is a loss | 74.00 |
| Coupon for a 98.00 fair value (2% margin) | 8.6897% p.a. |
| Coupon for a 100.00 fair value (no margin) | 10.6334% p.a. |

Outcome probabilities:

| Outcome | Probability |
|---|---|
| Called yr 1 (109) | 0.6562 |
| Called yr 2 (118) | 0.1489 |
| Coupon at yr 3 (127) | 0.0660 |
| Par at yr 3 (100) | 0.0955 |
| Loss at yr 3 (<100) | 0.0334 |

Barrier monitoring convention:

| barrier | price | prob_ki | prob_loss |
|---|---|---|---|
| Daily closes (base) | 98.3364 | 0.0346 | 0.0334 |
| Final fixing only | 98.6834 | 0.0116 | 0.0116 |
