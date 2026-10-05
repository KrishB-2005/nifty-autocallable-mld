## Layer 3b: Greeks

Flat market for the estimator comparison: spot 22,421.95, r = 6.4500%,
q = -0.2909%, vol = 13.8760% (the calibrated 3y values). 400,000 paths.

### Vanilla 3y ATM call

| greek | closed_form | pathwise | pathwise_se | lr | lr_se |
|---|---|---|---|---|---|
| Delta | 0.8392 | 0.8401 | 0.0004 | 0.8374 | 0.0026 |
| Vega (per vol pt) | 98.4343 | 97.7107 | 0.5067 | 99.1165 | 2.0589 |

### The note (per 100 notional; delta per 1% spot move, vega per vol point)

| note | estimator | delta_1pct | delta_se | vega_1pt | vega_se |
|---|---|---|---|---|---|
| Final-fixing barrier | Semi-analytic (bumped) | 0.2972 | 0.0000 | -0.4384 | 0.0000 |
| Final-fixing barrier | FD with CRN | 0.3037 | 0.0029 | -0.4468 | 0.0035 |
| Final-fixing barrier | Likelihood ratio | 0.2984 | 0.0015 | -0.4800 | 0.0376 |
| Daily barrier | FD with CRN | 0.3422 | 0.0030 | -0.5608 | 0.0036 |
| Daily barrier | Likelihood ratio | 0.3415 | 0.0185 | -0.9265 | 0.6169 |

On the coarse final-fixing grid the LR estimator is unbiased and usable. On the daily grid its
delta score is Z_1 / (sigma sqrt(dt_1)) with dt_1 = 1/252, and its vega score sums 756 terms, so
its standard error is many times FD-CRN's. The payoff jumps at every trigger, so pathwise
derivatives are not available for the note at all.

FD-CRN vs the semi-analytic Greeks over 8 further seeds: z-scores average -0.06 (delta)
and -0.16 (vega) with standard deviations 0.83 and 0.82,
so the table's single-seed gaps are noise, not bias.

### Risk profile across spot (calibrated market, daily barrier, FD with CRN)

| spot / S_ref | price | delta | vega |
|---|---|---|---|
| 0.6000 | 59.8153 | 0.6728 | 0.1168 |
| 0.6250 | 62.6149 | 0.7012 | 0.0892 |
| 0.6500 | 65.4320 | 0.7398 | 0.0646 |
| 0.6750 | 68.2887 | 0.7655 | 0.0108 |
| 0.7000 | 71.1382 | 1.0038 | -0.0504 |
| 0.7250 | 74.9920 | 1.0324 | -0.3438 |
| 0.7500 | 78.3639 | 0.9663 | -0.5412 |
| 0.7750 | 81.4793 | 0.9285 | -0.6568 |
| 0.8000 | 84.3386 | 0.8654 | -0.7215 |
| 0.8250 | 86.9221 | 0.8091 | -0.7585 |
| 0.8500 | 89.2277 | 0.7540 | -0.7729 |
| 0.8750 | 91.3262 | 0.6890 | -0.7662 |
| 0.9000 | 93.1714 | 0.6222 | -0.7521 |
| 0.9250 | 94.7840 | 0.5585 | -0.7244 |
| 0.9500 | 96.1670 | 0.4850 | -0.6781 |
| 0.9750 | 97.3473 | 0.4158 | -0.6309 |
| 1.0000 | 98.3369 | 0.3608 | -0.5649 |
| 1.0250 | 99.1312 | 0.2887 | -0.4927 |
| 1.0500 | 99.7774 | 0.2450 | -0.4431 |
| 1.0750 | 100.2958 | 0.1981 | -0.3811 |
| 1.1000 | 100.6891 | 0.1517 | -0.3103 |
| 1.1250 | 100.9975 | 0.1177 | -0.2620 |
| 1.1500 | 101.2263 | 0.0899 | -0.2089 |
| 1.1750 | 101.3917 | 0.0667 | -0.1641 |
| 1.2000 | 101.5183 | 0.0502 | -0.1276 |
| 1.2250 | 101.6020 | 0.0338 | -0.0934 |
| 1.2500 | 101.6574 | 0.0240 | -0.0684 |
| 1.2750 | 101.6999 | 0.0171 | -0.0509 |
| 1.3000 | 101.7261 | 0.0110 | -0.0379 |
