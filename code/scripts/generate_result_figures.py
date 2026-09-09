"""Render Paper A result figures 6–11 from the published kind-seed numbers."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parents[2] / "images"


def fig6() -> None:
    versions = ["v1", "v2", "v3", "v4", "v5"]
    f1 = [0.783, 0.948, 0.000, 0.716, 0.763]
    acc = [0.773, 0.907, 0.978, 0.662, 0.782]
    prec = [0.724, 0.919, 0.000, 0.585, 0.745]
    rec = [0.852, 0.980, 0.000, 0.923, 0.782]
    auc = [0.858, 0.921, 0.692, 0.780, 0.863]
    outcomes = ["PASS\nchampion", "PASS\nrolled back", "FAIL\nparadox", "FAIL\nP/reg.", "FAIL\nrecall"]
    x = list(range(len(versions)))
    w = 0.16
    fig, ax = plt.subplots(figsize=(9.2, 4.4))
    ax.bar([i - 2 * w for i in x], f1, w, label="Test F1", color="#1f4e79")
    ax.bar([i - w for i in x], acc, w, label="Accuracy", color="#9e480e")
    ax.bar(x, prec, w, label="Precision", color="#548235")
    ax.bar([i + w for i in x], rec, w, label="Recall", color="#7030a0")
    ax.bar([i + 2 * w for i in x], auc, w, label="ROC-AUC", color="#7f7f7f")
    ax.axhline(0.70, color="#1f4e79", ls="--", lw=0.8, alpha=0.7)
    ax.axhline(0.60, color="#548235", ls=":", lw=0.8, alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{v}\n{o}" for v, o in zip(versions, outcomes)])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Score")
    ax.set_title("churn-predictor held-out metrics by version (kind seed)")
    ax.legend(ncol=5, fontsize=8, loc="upper center")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "6-version-metrics.png", dpi=200)
    plt.close()


def fig7() -> None:
    scen = ["healthy\n(ref)", "volume\nanomaly", "feature\ndrift", "label\nimbalance", "regression", "later\nhealthy"]
    psi = [0.000, 0.041, 0.783, 0.064, 0.008, 0.011]
    colors = ["#548235" if p < 0.10 else "#c45911" if p < 0.25 else "#c00000" for p in psi]
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    ax.bar(range(len(scen)), psi, color=colors, edgecolor="black", linewidth=0.4)
    ax.axhline(0.10, color="#c45911", ls="--", lw=1, label="WARNING 0.10")
    ax.axhline(0.25, color="#c00000", ls="--", lw=1, label="SIGNIFICANT 0.25")
    ax.set_xticks(range(len(scen)))
    ax.set_xticklabels(scen)
    ax.set_ylabel("Mean PSI vs first healthy")
    ax.set_title("Scenario mean PSI (live monitor aggregation)")
    ax.legend(frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "7-scenario-mean-psi.png", dpi=200)
    plt.close()


def fig8() -> None:
    feats = [
        "usage_score",
        "customer_satisfaction",
        "monthly_charges",
        "age",
        "tenure_days",
        "service_count",
        "support_tickets",
        "is_month_to_month",
    ]
    fp = [3.597, 2.617, 0.016, 0.016, 0.012, 0.005, 0.001, 0.000]
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    ys = list(range(len(feats)))
    ax.barh(ys, fp, color=["#c00000" if p >= 0.25 else "#548235" for p in fp], edgecolor="black", linewidth=0.4)
    ax.set_yticks(ys)
    ax.set_yticklabels(feats)
    ax.invert_yaxis()
    ax.axvline(0.10, color="#c45911", ls="--", lw=1, label="WARNING 0.10")
    ax.axvline(0.25, color="#c00000", ls="--", lw=1, label="SIGNIFICANT 0.25")
    ax.set_xlabel("PSI (feature_drift vs first healthy)")
    ax.set_title("Per-feature PSI on the SIGNIFICANT batch")
    ax.legend(frameon=False, loc="lower right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "8-feature-drift-psi.png", dpi=200)
    plt.close()


def fig9() -> None:
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    labels = ["Promoted (2)", "Rejected (3)", "Blocked (1)"]
    sizes = [2, 3, 1]
    ax.bar(labels, sizes, color=["#548235", "#c00000", "#c45911"], edgecolor="black", linewidth=0.4)
    ax.set_ylabel("Pipeline runs")
    ax.set_ylim(0, 4)
    ax.set_title("First-seed outcomes (n = 6)")
    for i, s in enumerate(sizes):
        ax.text(i, s + 0.08, str(s), ha="center")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "9-pipeline-outcomes.png", dpi=200)
    plt.close()


def fig10() -> None:
    seeds = ["r1", "r2", "r3", "r4", "r5"]
    healthy = [0.783, 0.829, 0.817, 0.790, 0.787]
    drift = [0.948, 0.958, 0.956, 0.953, 0.969]
    x = list(range(len(seeds)))
    w = 0.35
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    ax.bar([i - w / 2 for i in x], healthy, w, label="healthy baseline", color="#1f4e79")
    ax.bar([i + w / 2 for i in x], drift, w, label="feature_drift retrain", color="#548235")
    ax.axhline(0.70, color="#1f4e79", ls="--", lw=0.8, alpha=0.7, label="F1_min 0.70")
    ax.set_xticks(x)
    ax.set_xticklabels(seeds)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Test F1")
    ax.set_title("Five-seed F1 before and after feature_drift retrain")
    ax.legend(frameon=False, loc="lower right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "10-five-seed-f1.png", dpi=200)
    plt.close()


def fig11() -> None:
    seeds = ["r1", "r2", "r3", "r4", "r5"]
    psi = [0.783, 0.748, 0.808, 0.749, 0.745]
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    ax.bar(seeds, psi, color="#c00000", edgecolor="black", linewidth=0.4)
    ax.axhline(0.10, color="#c45911", ls="--", lw=1, label="WARNING 0.10")
    ax.axhline(0.25, color="#c00000", ls="--", lw=1, label="SIGNIFICANT 0.25")
    ax.set_ylabel("Mean PSI vs first healthy")
    ax.set_title("feature_drift mean PSI is SIGNIFICANT in all five seeds")
    ax.set_ylim(0, 1.0)
    ax.legend(frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "11-five-seed-psi.png", dpi=200)
    plt.close()


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    fig6()
    fig7()
    fig8()
    fig9()
    fig10()
    fig11()
    print("wrote", sorted(p.name for p in OUT.iterdir() if p.suffix == ".png" and p.stem[0].isdigit()))
