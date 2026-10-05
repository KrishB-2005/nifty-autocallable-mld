"""Pull the NIFTY futures and options rows out of an NSE F&O UDiFF bhavcopy.

Usage:
    python scripts/extract_bhavcopy.py BhavCopy_NSE_FO_0_0_0_YYYYMMDD_F_0000.csv.zip data/

The archive is published daily by NSE at
https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_<YYYYMMDD>_F_0000.csv.zip
"""
import sys
import zipfile
from pathlib import Path

import pandas as pd

COLS = ["TradDt", "FinInstrmTp", "TckrSymb", "XpryDt", "StrkPric", "OptnTp", "ClsPric",
        "SttlmPric", "UndrlygPric", "OpnIntrst", "TtlTradgVol"]


def main(src: str, out_dir: str) -> Path:
    src = Path(src)
    if src.suffix == ".zip":
        with zipfile.ZipFile(src) as z:
            df = pd.read_csv(z.open(z.namelist()[0]))
    else:
        df = pd.read_csv(src)
    rows = df[(df.TckrSymb == "NIFTY") & df.FinInstrmTp.isin(["IDO", "IDF"])][COLS]
    rows = rows.sort_values(["FinInstrmTp", "XpryDt", "StrkPric", "OptnTp"])
    date = rows.TradDt.iloc[0].replace("-", "")
    out = Path(out_dir) / f"nifty_fo_{date}.csv"
    rows.to_csv(out, index=False)
    print(f"wrote {len(rows)} rows to {out}")
    return out


if __name__ == "__main__":
    main(*sys.argv[1:3])
