## Layer 3a: variance reduction (256,000 paths, base-case note)

| Method | Price | SE (bp) | Variance reduction (x) | Seconds | Gain at equal time (x) |
|---|---|---|---|---|---|
| Plain MC | 98.352 | 1.925 | 1.000 | 3.679 | 1.000 |
| Antithetic | 98.340 | 1.806 | 1.136 | 2.175 | 1.921 |
| CV: ATM call | 98.352 | 1.807 | 1.135 | 3.695 | 1.130 |
| Antithetic + vanilla CVs | 98.346 | 1.065 | 3.269 | 2.229 | 5.395 |
| Antithetic + event CVs | 98.342 | 0.455 | 17.913 | 2.550 | 25.842 |

"Variance reduction" is plain-MC variance over method variance at the same N. "Gain at equal time"
also divides by run time, which is the number that matters when choosing a method.
Fitted log-log slopes of SE vs N (theory -0.5): Plain MC: -0.509, Antithetic: -0.504, CV: ATM call: -0.509, Antithetic + vanilla CVs: -0.498, Antithetic + event CVs: -0.518.
