## Layer 3a: variance reduction (256,000 paths, base-case note)

| Method | Price | SE (bp) | Variance reduction (x) | Seconds | Gain at equal time (x) |
|---|---|---|---|---|---|
| Plain MC | 98.430 | 1.907 | 1.000 | 3.420 | 1.000 |
| Antithetic | 98.414 | 1.795 | 1.129 | 2.721 | 1.419 |
| CV: ATM call | 98.430 | 1.793 | 1.131 | 3.437 | 1.125 |
| Antithetic + vanilla CVs | 98.423 | 1.072 | 3.167 | 2.760 | 3.925 |
| Antithetic + event CVs | 98.415 | 0.451 | 17.844 | 3.193 | 19.113 |

"Variance reduction" is plain-MC variance over method variance at the same N. "Gain at equal time"
also divides by run time, which is the number that matters when choosing a method.
Fitted log-log slopes of SE vs N (theory -0.5): Plain MC: -0.510, Antithetic: -0.502, CV: ATM call: -0.509, Antithetic + vanilla CVs: -0.500, Antithetic + event CVs: -0.516.
