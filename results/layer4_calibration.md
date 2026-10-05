## Layer 4: calibration to the NSE option chain, 1 Oct 2026 (NIFTY 22,421.95)

1,008 traded NIFTY options with at least 7 days to expiry; 629 OTM quotes gave an implied vol.

### Forwards

| expiry | T | F | source | n_pairs | carry | r | q_implied |
|---|---|---|---|---|---|---|---|
| 2026-10-13 | 0.0329 | 22490.1726 | put-call parity | 62 | 0.0924 | 0.0550 | -0.0374 |
| 2026-10-19 | 0.0493 | 22509.0181 | put-call parity | 39 | 0.0786 | 0.0550 | -0.0236 |
| 2026-10-27 | 0.0712 | 22530.3000 | future | 77 | 0.0677 | 0.0550 | -0.0127 |
| 2026-11-03 | 0.0904 | 22556.5604 | put-call parity | 26 | 0.0662 | 0.0550 | -0.0112 |
| 2026-11-23 | 0.1452 | 22638.0000 | future | 51 | 0.0660 | 0.0550 | -0.0110 |
| 2026-12-29 | 0.2438 | 22779.3000 | future | 62 | 0.0648 | 0.0550 | -0.0098 |
| 2027-03-30 | 0.4932 | 23156.2769 | put-call parity | 3 | 0.0653 | 0.0565 | -0.0089 |
| 2027-06-29 | 0.7425 | 23490.8604 | put-call parity | 1 | 0.0627 | 0.0578 | -0.0049 |
| 2027-12-28 | 1.2411 | 24173.4967 | put-call parity | 2 | 0.0606 | 0.0599 | -0.0007 |
| 2028-12-26 | 2.2384 | 25936.6611 | put-call parity | 1 | 0.0651 | 0.0628 | -0.0023 |
| 2029-12-24 | 3.2329 | 27950.8892 | put-call parity | 1 | 0.0682 | 0.0651 | -0.0030 |

NIFTY forwards imply about 6.5% carry, at or above the INR zero curve, so the implied dividend yield is
slightly negative. Index futures in India usually trade rich to G-secs. The pricer takes forwards
from the market, since futures are the hedge, and discounts on the rate curve.

### Smiles (quadratic in k = ln(K/F), fitted on |k| <= 0.3)

| expiry | T | n | atm_vol | skew | curvature | rmse |
|---|---|---|---|---|---|---|
| 2026-10-13 | 0.0329 | 106 | 0.1367 | -0.2355 | 9.5234 | 0.0052 |
| 2026-10-19 | 0.0493 | 82 | 0.1366 | -0.2654 | 8.2934 | 0.0051 |
| 2026-10-27 | 0.0712 | 122 | 0.1405 | -0.2208 | 4.5699 | 0.0074 |
| 2026-11-03 | 0.0904 | 69 | 0.1370 | -0.2512 | 5.3319 | 0.0057 |
| 2026-11-23 | 0.1452 | 109 | 0.1328 | -0.2085 | 3.5412 | 0.0022 |
| 2026-12-29 | 0.2438 | 87 | 0.1295 | -0.1198 | 1.6310 | 0.0050 |
| 2027-03-30 | 0.4932 | 9 | 0.1275 | -0.0867 | 0.9563 | 0.0024 |
| 2027-06-29 | 0.7425 | 6 | 0.1201 | -0.1114 | 1.1512 | 0.0013 |
| 2027-12-28 | 1.2411 | 14 | 0.1303 | -0.0843 | 0.4021 | 0.0073 |
| 2028-12-26 | 2.2384 | 9 | 0.1388 | -0.1029 | 0.0142 | 0.0052 |

### How much the vol input matters for this note

| vol_input | vol | price | diff_vs_base |
|---|---|---|---|
| Calibrated ATM term structure (base) | 0.1388 | 98.3524 | 0.0000 |
| Flat, Dec-2028 smile at K = 100% of spot | 0.1541 | 97.1931 | -1.1593 |
| Flat, Dec-2028 smile at K = 85% of spot (extrapolated, k < -0.3) | 0.1718 | 96.0636 | -2.2887 |
| Flat, Dec-2028 smile at K = 70% of spot (extrapolated, k < -0.3) | 0.1941 | 94.6130 | -3.7394 |

The knock-in sits deep in the put wing, where implied vol is well above ATM, so an ATM-vol model
overvalues the note to the investor. A local or stochastic vol model calibrated to the whole smile
is the fix; see "What breaks this model" in the README.
