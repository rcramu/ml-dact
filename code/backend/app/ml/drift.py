"""Statistical drift detection - PSI, KS test, categorical drift (paper Section 8).

Implements the PSI/KS formulas from the paper directly with scipy/numpy rather
than a heavier drift-monitoring library, matching this codebase's convention
of implementing the core statistical method from scratch.
"""
import numpy as np
from scipy import stats

_EPS = 1e-6


def psi_numeric(reference: np.ndarray, production: np.ndarray, bins: int = 10) -> float:
    """Population Stability Index (paper Section 8): PSI = sum (P_i - Q_i) * ln(P_i / Q_i)."""
    if len(reference) == 0 or len(production) == 0:
        return 0.0
    quantiles = np.unique(np.quantile(reference, np.linspace(0, 1, bins + 1)))
    if len(quantiles) < 3:
        return 0.0
    quantiles[0], quantiles[-1] = -np.inf, np.inf
    ref_counts, _ = np.histogram(reference, bins=quantiles)
    prod_counts, _ = np.histogram(production, bins=quantiles)
    ref_pct = ref_counts / max(ref_counts.sum(), 1) + _EPS
    prod_pct = prod_counts / max(prod_counts.sum(), 1) + _EPS
    return float(np.sum((prod_pct - ref_pct) * np.log(prod_pct / ref_pct)))


def ks_test(reference: np.ndarray, production: np.ndarray) -> tuple[float, float]:
    """Kolmogorov-Smirnov two-sample test for numerical distributions (paper Section 8)."""
    if len(reference) < 2 or len(production) < 2:
        return 0.0, 1.0
    result = stats.ks_2samp(reference, production)
    return float(result.statistic), float(result.pvalue)


def drift_level(psi: float, psi_warning: float = 0.10, psi_critical: float = 0.25) -> str:
    """Paper Section 8 threshold table: PSI < 0.10 Normal, 0.10-0.25 Warning, > 0.25 Significant."""
    if psi >= psi_critical:
        return "SIGNIFICANT"
    if psi >= psi_warning:
        return "WARNING"
    return "NORMAL"
