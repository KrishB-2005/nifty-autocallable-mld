"""Regenerate every figure and results table, in layer order.

    python scripts/run_all.py
"""
import runpy
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = [
    "layer1_convergence.py",
    "layer2_autocall.py",
    "layer3_variance_reduction.py",
    "layer3_greeks.py",
    "layer3_scenarios.py",
    "layer4_calibration.py",
    "../validation/quantlib_check.py",
]

if __name__ == "__main__":
    for step in STEPS:
        t = time.perf_counter()
        print(f"\n== {step}")
        runpy.run_path(str(HERE / step), run_name="__main__")
        print(f"   done in {time.perf_counter() - t:.0f}s")
