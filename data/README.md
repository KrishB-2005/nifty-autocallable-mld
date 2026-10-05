# Data

`nifty_fo_20261001.csv` holds the NIFTY index futures (`IDF`) and index options (`IDO`) rows
from the NSE F&O UDiFF bhavcopy for 1 October 2026
(`BhavCopy_NSE_FO_0_0_0_20261001_F_0000.csv.zip` from the NSE archives). Columns are kept as
NSE names them. NIFTY closed at 22,421.95 that day.

Only rows with `TtlTradgVol > 0` are used for calibration. For strikes that did not trade,
NSE's `ClsPric`/`SttlmPric` are exchange-computed theoretical values, not market prices.

`inr_zero_curve.csv` is an approximate INR sovereign zero curve. See the header of that
file for how it was put together and what to replace it with.

To use a different day, download that day's F&O bhavcopy and run
`python scripts/extract_bhavcopy.py <zip> data/` (see the script for details).
