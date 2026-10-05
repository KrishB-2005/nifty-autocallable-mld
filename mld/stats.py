"""Monte Carlo estimate with its standard error."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MCResult:
    value: float
    stderr: float
    n: int            # number of i.i.d. samples behind the estimate (antithetic pairs count once)

    def ci(self, z: float = 1.96):
        return self.value - z * self.stderr, self.value + z * self.stderr

    def __str__(self):
        return f"{self.value:.4f} +/- {self.stderr:.4f}"


def estimate(samples: np.ndarray) -> MCResult:
    samples = np.asarray(samples, dtype=float)
    n = samples.shape[0]
    return MCResult(float(samples.mean()), float(samples.std(ddof=1) / np.sqrt(n)), n)
