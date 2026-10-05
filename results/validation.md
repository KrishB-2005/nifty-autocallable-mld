| Check | Case | Ours | QuantLib | Diff (bp) | Combined MC SE (bp) | abs(z) | Unit |
|---|---|---:|---:|---:|---:|---:|---|
| Bond leg | ZCB 0.50y, 100 face | 97.222054 | 97.222054 | +0.00 |  |  | bp of price |
| Bond leg | ZCB 1.00y, 100 face | 94.317824 | 94.317824 | +0.00 |  |  | bp of price |
| Bond leg | ZCB 3.00y, 100 face | 82.406984 | 82.406984 | +0.00 |  |  | bp of price |
| Bond leg | ZCB 4.50y, 100 face | 73.839626 | 73.839626 | +0.00 |  |  | bp of price |
| Vanilla (calibrated mkt) | ATM call 3y, Black-Scholes | 4687.557454 | 4687.557454 | +0.00 |  |  | bp of price |
| Vanilla (calibrated mkt) | ATM call 3y, our MC 400,000 | 4683.804370 | 4687.557454 | -8.01 | 8.35 | 0.96 | bp of price |
| Vanilla (calibrated mkt) | 85% put 3y, Black-Scholes | 126.844050 | 126.844050 | +0.00 |  |  | bp of price |
| Vanilla (calibrated mkt) | 85% put 3y, our MC 400,000 | 126.503341 | 126.844050 | -26.86 | 68.19 | 0.39 | bp of price |
| Digitals | Cash-or-nothing call @100%, 3y | 0.630103 | 0.630103 | +0.00 |  |  | bp of 1 unit cash |
| Digitals | Asset-or-nothing put @70%, 3y | 163.525086 | 163.525086 | +0.00 |  |  | bp of price |
| Down-and-in put 100/70, 3y | vs QL MC, daily monitoring | 177.988779 | 172.274953 | +331.67 | 244.72 | 1.36 | bp of price |
| Down-and-in put 100/70, 3y | vs QL analytic, BGK-shifted barrier | 177.988779 | 177.175400 | +45.91 | 85.57 | 0.54 | bp of price |
| Down-and-in put 100/70, 3y | vs QL analytic, continuous (no shift) | 177.988779 | 184.524857 | -354.21 | 82.16 | 4.31 | bp of price |
| Autocall, 1 observation | our MC vs QL digital decomposition | 99.019780 | 99.018744 | +0.10 | 0.26 | 0.39 | bp of notional |
| Autocall 3y, daily KI | our paths vs QuantLib paths | 98.346491 | 98.328143 | +1.83 | 3.84 | 0.48 | bp of notional |
