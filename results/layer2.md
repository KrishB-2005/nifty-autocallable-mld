## Layer 2: base-case note on the 1 Oct 2026 market

Term sheet: 3y on NIFTY 50, initial fixing 22,421.95, annual observations, autocall at 100%,
9% p.a. snowball coupon, 70% knock-in on daily closes, issuer spread 100bp.
400,000 paths, antithetic with control variates.

| Item | Value (per 100) |
|---|---|
| Note fair value | 98.4009 +/- 0.0086 |
| Zero-coupon bond leg (100 at 3y, issuer curve) | 79.9715 |
| Derivative overlay (note minus bond) | +18.4294 |
| Structuring margin at issue price 100 | 1.5991 |
| Expected life | 1.53 years |
| Probability the barrier is ever touched | 3.90% |
| Probability of capital loss | 3.29% |
| Average redemption when there is a loss | 74.02 |
| Coupon for a 98.00 fair value (2% margin) | 8.6219% p.a. |
| Coupon for a 100.00 fair value (no margin) | 10.5663% p.a. |

Outcome probabilities:

| Outcome | Probability |
|---|---|
| Called yr 1 (109) | 0.6612 |
| Called yr 2 (118) | 0.1480 |
| Coupon at yr 3 (127) | 0.0645 |
| Par at yr 3 (100) | 0.0933 |
| Loss at yr 3 (<100) | 0.0329 |

Barrier monitoring convention:

| barrier | price | prob_ki | prob_loss |
|---|---|---|---|
| Daily closes (base) | 98.4009 | 0.0390 | 0.0329 |
| Final fixing only | 98.7460 | 0.0134 | 0.0114 |
