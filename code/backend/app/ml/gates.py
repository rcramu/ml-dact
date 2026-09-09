"""Evaluation / regression / deployment gates (req.md Sec. 21-23)."""
from ..config import settings


def evaluation_gate(candidate: dict, champion: dict | None) -> tuple[str, float | None, str]:
    """req.md Sec. 21-23 multi-metric gate.

    Returns (gate_result, regression_pct, reasons).
    """
    reasons = []

    if candidate["f1"] < settings.minimum_f1:
        reasons.append(f"candidate F1 {candidate['f1']:.3f} below minimum {settings.minimum_f1:.3f}")
    if candidate["recall"] < settings.minimum_recall:
        reasons.append(f"candidate recall {candidate['recall']:.3f} below minimum {settings.minimum_recall:.3f}")
    if candidate["precision"] < settings.minimum_precision:
        reasons.append(f"candidate precision {candidate['precision']:.3f} below minimum {settings.minimum_precision:.3f}")

    regression_pct = None
    if champion is not None and champion.get("f1", 0) > 0:
        regression_pct = round(((champion["f1"] - candidate["f1"]) / champion["f1"]) * 100, 2)
        if regression_pct > settings.max_regression_pct:
            reasons.append(
                f"F1 regression {regression_pct:.2f}% exceeds max allowed {settings.max_regression_pct:.2f}% "
                f"(champion {champion['f1']:.3f} -> candidate {candidate['f1']:.3f})"
            )
        if candidate["recall"] < champion.get("recall", 0):
            reasons.append(f"candidate recall {candidate['recall']:.3f} below champion recall {champion['recall']:.3f}")

    result = "FAIL" if reasons else "PASS"
    if result == "PASS":
        reasons_text = "All gate conditions satisfied: minimum F1/precision/recall met" + (
            f" and regression {regression_pct:.2f}% within {settings.max_regression_pct:.2f}% budget." if regression_pct is not None else " (first version — no champion to compare against)."
        )
    else:
        reasons_text = "; ".join(reasons)
    return result, regression_pct, reasons_text
