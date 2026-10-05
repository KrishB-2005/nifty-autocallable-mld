## Layer 1: bond leg and vanilla anchor (market of 22,421.95, 1 Oct 2026)

| Item | Value |
|---|---|
| ZCB, 100 face, 3y, risk-free curve | 82.4070 |
| ZCB, 100 face, 3y, curve + 100bp issuer spread | 79.9715 |
| 3y forward | 27,447.28 |
| 3y ATM vol (calibrated) | 0.1388 |
| ATM call, Black-Scholes | 4687.5575 |
| ATM call, MC 2,000,000 antithetic | 4686.9892 +/- 1.7448 (-0.33 SE) |
| Fitted log-log slope of RMS error vs N | -0.548 (theory: -0.5) |

| Paths N | RMS error (bp) | Mean reported SE (bp) |
|---|---|---|
| 1,000 | 376.73 | 329.36 |
| 4,000 | 143.29 | 163.78 |
| 16,000 | 71.21 | 82.07 |
| 64,000 | 42.29 | 40.94 |
| 256,000 | 17.92 | 20.48 |
| 1,024,000 | 7.16 | 10.24 |
