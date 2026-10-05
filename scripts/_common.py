"""Shared setup for the analysis scripts: paths, the base-case note, plot style."""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
FIG = ROOT / "figures"
RES = ROOT / "results"
FIG.mkdir(exist_ok=True)
RES.mkdir(exist_ok=True)

from mld.autocall import AutocallSpec  # noqa: E402

# Base-case product: 3y NIFTY autocallable, annual observations, 100% trigger,
# 9% p.a. snowball coupon, 70% knock-in on daily closes. Issuer spread 1%.
SPEC = AutocallSpec(obs_times=(1.0, 2.0, 3.0), autocall_levels=1.0, coupon_rate=0.09,
                    ki_barrier=0.70, ki_daily=True)
SPREAD = 0.01

# Categorical slots (fixed order) and text colours from the validated palette
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
    "lines.linewidth": 2.0, "lines.markersize": 6, "font.size": 10, "axes.titlesize": 11,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "legend.frameon": False,
})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / name, dpi=160)
    plt.close(fig)
    print(f"wrote figures/{name}")


def write_md(name, text):
    (RES / name).write_text(text.strip() + "\n")
    print(f"wrote results/{name}")


def df_to_md(df, floatfmt=".4f"):
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cells = [format(v, floatfmt) if isinstance(v, float) else str(v) for v in r.values]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)
