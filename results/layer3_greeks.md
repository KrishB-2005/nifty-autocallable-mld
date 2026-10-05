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
| 0.6000 | 59.8243 | 0.6694 | 0.1175 |
| 0.6250 | 62.6070 | 0.7009 | 0.0887 |
| 0.6500 | 65.4380 | 0.7458 | 0.0655 |
| 0.6750 | 68.2882 | 0.7720 | 0.0156 |
| 0.7000 | 71.1364 | 1.0170 | -0.0442 |
| 0.7250 | 74.9898 | 1.0370 | -0.3438 |
| 0.7500 | 78.3816 | 0.9719 | -0.5427 |
| 0.7750 | 81.4906 | 0.9234 | -0.6578 |
| 0.8000 | 84.3475 | 0.8674 | -0.7215 |
| 0.8250 | 86.9237 | 0.8054 | -0.7527 |
| 0.8500 | 89.2603 | 0.7539 | -0.7734 |
| 0.8750 | 91.3585 | 0.6902 | -0.7703 |
| 0.9000 | 93.2185 | 0.6225 | -0.7495 |
| 0.9250 | 94.8476 | 0.5545 | -0.7185 |
| 0.9500 | 96.2255 | 0.4886 | -0.6761 |
| 0.9750 | 97.4146 | 0.4230 | -0.6252 |
| 1.0000 | 98.3996 | 0.3572 | -0.5634 |
| 1.0250 | 99.2043 | 0.2981 | -0.5029 |
| 1.0500 | 99.8489 | 0.2425 | -0.4357 |
| 1.0750 | 100.3616 | 0.1885 | -0.3661 |
| 1.1000 | 100.7540 | 0.1509 | -0.3088 |
| 1.1250 | 101.0536 | 0.1155 | -0.2522 |
| 1.1500 | 101.2705 | 0.0830 | -0.1975 |
| 1.1750 | 101.4267 | 0.0673 | -0.1569 |
| 1.2000 | 101.5464 | 0.0460 | -0.1187 |
| 1.2250 | 101.6189 | 0.0287 | -0.0841 |
| 1.2500 | 101.6705 | 0.0229 | -0.0633 |
| 1.2750 | 101.7103 | 0.0160 | -0.0473 |
| 1.3000 | 101.7354 | 0.0098 | -0.0330 |
