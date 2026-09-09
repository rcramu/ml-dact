"""Deterministic synthetic customer-churn data generator.

Implements the Section 7.1 dataset described in the paper ("A Production-Grade
Closed-Loop MLOps Architecture for Drift-Aware Continuous Training and
Deployment"): a synthetic customer-churn dataset with controlled drift
scenarios (Experiment A - no drift / B - moderate drift / C - severe drift),
plus the operational trigger scenarios used to exercise the closed-loop
pipeline (data-volume anomaly, class imbalance, training regression).
Every scenario accepts a deterministic seed so `docker compose up` always
reproduces the exact same ingested data and training outcomes.
"""
import numpy as np

FEATURE_NAMES = [
    "age", "tenure_days", "monthly_charges", "support_tickets",
    "usage_score", "service_count", "customer_satisfaction", "is_month_to_month",
]

# True underlying weights used to synthesize churn - kept private to the
# generator; the model must LEARN these from data, never see them directly.
# Order matches FEATURE_NAMES. Sign reflects real-world churn intuition: more
# tickets / higher charges / month-to-month contracts increase churn; longer
# tenure / higher usage / more bundled services / satisfaction reduce it.
_TRUE_WEIGHTS = np.array([-0.25, -1.5, 0.9, 1.7, -1.0, -1.1, -2.1, 1.4])
_BIAS = -0.9


def stable_seed(key: str) -> int:
    import hashlib
    return int(hashlib.sha256(key.encode()).hexdigest(), 16) % (2**31)


def _raw_features(rng: np.random.Generator, n: int) -> dict:
    age = rng.integers(18, 76, n)
    tenure_days = np.clip(rng.exponential(400, n), 1, 2600)
    monthly_charges = np.clip(rng.gamma(6.0, 14.0, n), 15, 200)
    support_tickets = rng.poisson(1.5, n)
    usage_score = np.clip(rng.normal(0.55, 0.2, n), 0, 1)
    service_count = rng.poisson(2.0, n)
    customer_satisfaction = np.clip(rng.normal(0.7, 0.15, n), 0, 1)
    is_month_to_month = (rng.random(n) < 0.4).astype(int)
    return {
        "age": age, "tenure_days": tenure_days, "monthly_charges": monthly_charges,
        "support_tickets": support_tickets, "usage_score": usage_score,
        "service_count": service_count, "customer_satisfaction": customer_satisfaction,
        "is_month_to_month": is_month_to_month,
    }


def _standardize(features: dict) -> np.ndarray:
    x = np.stack([
        (features["age"] - 45) / 15,
        (features["tenure_days"] - 400) / 350,
        (features["monthly_charges"] - 85) / 30,
        (features["support_tickets"] - 1.5) / 1.5,
        (features["usage_score"] - 0.55) / 0.2,
        (features["service_count"] - 2) / 1.5,
        (features["customer_satisfaction"] - 0.7) / 0.15,
        features["is_month_to_month"].astype(float),
    ], axis=1)
    return x


def _labels_from_features(rng: np.random.Generator, x: np.ndarray, noise_sigma: float) -> np.ndarray:
    logit = x @ _TRUE_WEIGHTS + _BIAS + rng.normal(0, noise_sigma, x.shape[0])
    p = 1 / (1 + np.exp(-logit))
    return (rng.random(x.shape[0]) < p).astype(int)


def generate_scenario(scenario: str, seed: int, expected_rows: int = 1500) -> list[dict]:
    """Returns a list of raw record dicts (features + label + split).

    Scenarios:
      healthy          - Experiment A (no drift): P_train(X) ~ P_prod(X).
      volume_anomaly    - operational trigger: only a fraction of expected rows ingested.
      feature_drift     - Experiment B/C (moderate/severe drift): customer_satisfaction and
                          usage_score distributions shift, as measured by PSI (Section 8).
      label_imbalance   - churn ratio forced down to a rare-event level.
      regression        - heavy label noise so any trained candidate underperforms the champion.
    """
    rng = np.random.default_rng(seed)
    n = expected_rows

    if scenario == "volume_anomaly":
        n = max(40, int(expected_rows * 0.12))
    elif scenario == "label_imbalance":
        n = expected_rows

    features = _raw_features(rng, n)

    if scenario == "feature_drift":
        # Section 7.1 Experiment C (severe drift): satisfaction and engagement collapse,
        # simulating a period of declining product experience ahead of a churn wave.
        features["customer_satisfaction"] = np.clip(rng.normal(0.40, 0.18, n), 0, 1)
        features["usage_score"] = np.clip(rng.normal(0.25, 0.15, n), 0, 1)

    x = _standardize(features)

    if scenario == "regression":
        labels = _labels_from_features(rng, x, noise_sigma=3.2)
    else:
        labels = _labels_from_features(rng, x, noise_sigma=0.35)

    if scenario == "label_imbalance":
        # Force a ~98/2 non-churn/churn split regardless of the logit, while padding the
        # majority class back up (via resampling with replacement) so the total row count
        # stays close to `n` - this scenario is about class balance, not data volume.
        target_churn = max(2, int(n * 0.02))
        churn_idx = np.where(labels == 1)[0]
        healthy_idx = np.where(labels == 0)[0]
        if len(churn_idx) > target_churn:
            keep_churn = rng.choice(churn_idx, size=target_churn, replace=False)
        else:
            keep_churn = churn_idx
        target_healthy = n - len(keep_churn)
        if len(healthy_idx) < target_healthy:
            pad = rng.choice(healthy_idx, size=target_healthy - len(healthy_idx), replace=True)
            keep_healthy = np.concatenate([healthy_idx, pad])
        else:
            keep_healthy = rng.choice(healthy_idx, size=target_healthy, replace=False)
        keep = np.concatenate([keep_healthy, keep_churn])
        rng.shuffle(keep)
        for k in features:
            features[k] = features[k][keep]
        labels = labels[keep]
        n = len(keep)

    order = rng.permutation(n)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)
    splits = np.empty(n, dtype=object)
    splits[order[:train_end]] = "train"
    splits[order[train_end:val_end]] = "val"
    splits[order[val_end:]] = "test"

    records = []
    for i in range(n):
        records.append({
            "split": str(splits[i]),
            "age": int(features["age"][i]),
            "tenure_days": int(features["tenure_days"][i]),
            "monthly_charges": round(float(features["monthly_charges"][i]), 2),
            "support_tickets": int(features["support_tickets"][i]),
            "usage_score": round(float(features["usage_score"][i]), 4),
            "service_count": int(features["service_count"][i]),
            "customer_satisfaction": round(float(features["customer_satisfaction"][i]), 4),
            "is_month_to_month": bool(features["is_month_to_month"][i]),
            "label": int(labels[i]),
        })
    return records


def records_to_arrays(records: list[dict], split: str | None = None):
    """Converts stored RawRecord-shaped dicts back into (X, y) numpy arrays for training/eval."""
    rows = [r for r in records if split is None or r["split"] == split]
    features = {
        "age": np.array([r["age"] for r in rows], dtype=float),
        "tenure_days": np.array([r["tenure_days"] for r in rows], dtype=float),
        "monthly_charges": np.array([r["monthly_charges"] for r in rows], dtype=float),
        "support_tickets": np.array([r["support_tickets"] for r in rows], dtype=float),
        "usage_score": np.array([r["usage_score"] for r in rows], dtype=float),
        "service_count": np.array([r["service_count"] for r in rows], dtype=float),
        "customer_satisfaction": np.array([r["customer_satisfaction"] for r in rows], dtype=float),
        "is_month_to_month": np.array([int(r["is_month_to_month"]) for r in rows], dtype=float),
    }
    x = np.stack([
        (features["age"] - 45) / 15,
        (features["tenure_days"] - 400) / 350,
        (features["monthly_charges"] - 85) / 30,
        (features["support_tickets"] - 1.5) / 1.5,
        (features["usage_score"] - 0.55) / 0.2,
        (features["service_count"] - 2) / 1.5,
        (features["customer_satisfaction"] - 0.7) / 0.15,
        features["is_month_to_month"],
    ], axis=1) if rows else np.zeros((0, 8))
    y = np.array([r["label"] for r in rows], dtype=int)
    return x, y

