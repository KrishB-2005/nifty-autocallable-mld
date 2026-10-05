## Layer 3a: variance reduction (256,000 paths, base-case note)

| Method | Price | SE (bp) | Variance reduction (x) | Seconds | Gain at equal time (x) |
|---|---|---|---|---|---|
| Plain MC | 98.352 | 1.925 | 1.000 | 3.523 | 1.000 |
| Antithetic | 98.340 | 1.806 | 1.136 | 1.889 | 2.118 |
| CV: ATM call | 98.352 | 1.807 | 1.135 | 3.551 | 1.126 |
| Antithetic + vanilla CVs | 98.346 | 1.065 | 3.269 | 1.959 | 5.880 |
| Antithetic + event CVs | 98.342 | 0.455 | 17.913 | 2.149 | 29.364 |

"Variance reduction" is plain-MC variance over method variance at the same N. "Gain at equal time"
also divides by run time, which is the number that matters when choosing a method.
Fitted log-log slopes of SE vs N (theory -0.5): Plain MC: -0.509, Antithetic: -0.504, CV: ATM call: -0.509, Antithetic + vanilla CVs: -0.498, Antithetic + event CVs: -0.518.
