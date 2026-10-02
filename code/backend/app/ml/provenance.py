"""EXP-05/EXP-07 provenance stamps: which policy code and threshold values
produced a given decision, so it can be traced and replayed later.

The backend container does not have a .git directory (the Docker build
context is backend/ only), so the commit hash is passed in from the host at
`docker compose up` time via CTP_POLICY_VERSION rather than read from git
inside the container.
"""
from __future__ import annotations

import hashlib

from ..config import settings
from .drift import drift_level  # noqa: F401  (defaults documented below)

# drift_level()'s PSI thresholds are function defaults, not settings-configurable
# today -- that is itself an EXP-03 finding, not fixed here. Included explicitly
# in the hash so a future change to those defaults changes threshold_config_version.
_PSI_WARNING_DEFAULT = 0.10
_PSI_CRITICAL_DEFAULT = 0.25


def policy_version() -> str:
    return f"app.ml.policy@{settings.policy_version}"


def threshold_config_version() -> str:
    payload = "|".join(
        str(v)
        for v in (
            settings.minimum_f1,
            settings.minimum_precision,
            settings.minimum_recall,
            settings.max_regression_pct,
            _PSI_WARNING_DEFAULT,
            _PSI_CRITICAL_DEFAULT,
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:12]
