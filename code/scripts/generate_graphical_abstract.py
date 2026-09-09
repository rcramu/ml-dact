"""Wide graphical abstract from published case-study numbers (not generative artwork)."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parents[2] / "images" / "graphical-abstract.png"


def box(ax, xy, w, h, text, facecolor, fontsize=11):
    patch = FancyBboxPatch(
        xy,
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.1,
        edgecolor="#1f4e79",
        facecolor=facecolor,
    )
    ax.add_patch(patch)
    ax.text(
        xy[0] + w / 2,
        xy[1] + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color="#1a1a1a",
        wrap=True,
    )


def main() -> None:
    # Elsevier-friendly wide banner (~1328 x 531 px at 200 dpi)
    fig, ax = plt.subplots(figsize=(6.64, 2.655), dpi=200)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    ax.text(
        5,
        3.72,
        "Drift-aware, quality-gated continuous training  ·  observational case study",
        ha="center",
        va="center",
        fontsize=9.5,
        color="#1f4e79",
        fontweight="bold",
    )

    box(ax, (0.25, 1.85), 2.2, 1.35, "Monitor\nmean PSI / KS", "#d6eaf8", 10)
    box(ax, (2.85, 1.85), 2.2, 1.35, "Retrain\nAirflow + PyTorch", "#d5f5e3", 10)
    box(ax, (5.45, 1.85), 2.2, 1.35, "Algorithm 1\nF1 / P / R + budget", "#fdebd0", 10)
    box(ax, (8.05, 1.85), 1.7, 1.35, "Promote\nor reject", "#f5b7b1", 10)
    for x in (2.45, 5.05, 7.65):
        ax.annotate("", xy=(x + 0.38, 2.52), xytext=(x, 2.52), arrowprops=dict(arrowstyle="->", color="#1f4e79", lw=1.4))

    ax.text(
        5,
        1.15,
        "5 protocol replicates  ·  30 runs  ·  1 synthetic generator  ·  kind (not Amazon EKS)",
        ha="center",
        va="center",
        fontsize=8.5,
        color="#333333",
    )
    ax.text(
        5,
        0.45,
        "Drift retrain: mean F1 0.801 → 0.957 (5/5)     Accuracy-only would pass 8/13 rejects     Gate passed 0/13",
        ha="center",
        va="center",
        fontsize=8.2,
        color="#1f4e79",
    )
    fig.tight_layout(pad=0.25)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=200)
    plt.close()
    print("wrote", OUT)


if __name__ == "__main__":
    main()
