"""Classification metrics for candidate/champion evaluation (req.md Sec. 20, 25)."""
import numpy as np
from sklearn.metrics import (
    accuracy_score, average_precision_score, f1_score, precision_score,
    recall_score, roc_auc_score,
)


def classification_metrics(probs, predictions, ground_truth) -> dict:
    y_true = np.asarray(ground_truth)
    y_pred = np.asarray(predictions)
    y_prob = np.asarray(probs)
    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }
    try:
        if len(set(y_true.tolist())) > 1:
            metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob))
            metrics["pr_auc"] = float(average_precision_score(y_true, y_prob))
        else:
            metrics["roc_auc"] = 0.0
            metrics["pr_auc"] = 0.0
    except ValueError:
        metrics["roc_auc"] = 0.0
        metrics["pr_auc"] = 0.0
    return metrics
