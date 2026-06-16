"""Shared evaluation helpers for the v2 model-retraining scripts.

Adds research-grade metrics (PR-AUC, pseudo-R^2 variants, Brier score)
on top of the basic accuracy/F1/ROC-AUC that the original training
scripts produced.
"""
import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, brier_score_loss,
)


def efron_r2(y_true, y_prob):
    """Efron's pseudo-R^2: 1 - SS_res/SS_tot computed on predicted probabilities.

    This is the classic R^2 formula applied directly to the model's
    probability output, giving an "R-squared" figure that is directly
    comparable in spirit to a regression R^2.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    ss_res = np.sum((y_true - y_prob) ** 2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    if ss_tot == 0:
        return 0.0
    return float(1 - ss_res / ss_tot)


def mcfadden_r2(y_true, y_prob):
    """McFadden's pseudo-R^2 based on log-likelihood vs. the null model."""
    eps = 1e-15
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.clip(np.asarray(y_prob, dtype=float), eps, 1 - eps)
    ll_model = np.sum(y_true * np.log(y_prob) + (1 - y_true) * np.log(1 - y_prob))
    p_null = np.clip(y_true.mean(), eps, 1 - eps)
    ll_null = np.sum(y_true * np.log(p_null) + (1 - y_true) * np.log(1 - p_null))
    if ll_null == 0:
        return 0.0
    return float(1 - ll_model / ll_null)


def extended_metrics(y_true, y_prob, threshold=0.5, n_train=None, n_test=None, extra=None):
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    y_pred = (y_prob >= threshold).astype(int)

    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else 0.0,
        "pr_auc": float(average_precision_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else 0.0,
        "r_squared": efron_r2(y_true, y_prob),
        "mcfadden_r2": mcfadden_r2(y_true, y_prob),
        "brier_score": float(brier_score_loss(y_true, y_prob)),
    }
    if n_train is not None:
        metrics["n_train"] = int(n_train)
    if n_test is not None:
        metrics["n_test"] = int(n_test)
    if extra:
        metrics.update(extra)
    return metrics
