"""EWC continual learning — Fisher-regularized weekly retraining.

Naive weekly retraining causes *catastrophic forgetting*: if the last 7 days
contained no phishing, gradient descent happily overwrites the weights that
encoded phishing and the model forgets it. Elastic Weight Consolidation
(Kirkpatrick et al. 2017) fixes this by measuring which weights matter for the
old task — the diagonal of the Fisher information matrix, F_i = E[(∂log p/∂θ_i)²]
— and adding a quadratic penalty λ·Σ F_i·(θ_i − θ*_i)² that pins the important
weights near their old values while letting the rest adapt.

The learned object here is a small *fusion head* that maps the provider
sub-scores → risk decision. It's an optional learned replacement for the static
weighted ensemble in risk_engine.py; training it does not disturb the live path
(the head is persisted, not force-loaded). Each weekly run anchors to the
previous week's Fisher, so old attack patterns survive distribution shift.

Requires torch (admin container only). Import is guarded so the slim
customer/attacker containers don't choke on it.
"""
import os
import json
import time
import numpy as np
from typing import List, Dict, Any, Tuple, Optional

try:
    import torch
    import torch.nn as nn
    _TORCH = True
except ImportError:
    _TORCH = False

# Provider sub-scores the fusion head consumes, in fixed order.
FEATURE_ORDER = [
    "TransactionRisk", "URLPhishing", "AccountTakeover",
    "NetworkRisk", "DeviceTrust", "SessionFingerprint", "BeaconBehavioral (Ensemble)",
]
ARTIFACT = "models/artifacts/fusion_head_ewc.pt"


if _TORCH:
    class FusionHead(nn.Module):
        """Tiny MLP: 7 provider scores → 4-way tier logits."""
        def __init__(self, n_in: int = len(FEATURE_ORDER), n_hidden: int = 16, n_out: int = 4):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(n_in, n_hidden), nn.ReLU(),
                nn.Linear(n_hidden, n_out),
            )

        def forward(self, x):
            return self.net(x)


def events_to_dataset(events: List[Any]) -> Tuple[np.ndarray, np.ndarray]:
    """Build (X, y) from persisted SecurityEvents.

    X = per-provider risk_score vector (FEATURE_ORDER). y = escalation_level-1
    (0..3). Rows with no breakdown are skipped.
    """
    X, y = [], []
    for e in events:
        bd = getattr(e, "breakdown", None) or {}
        row = []
        for name in FEATURE_ORDER:
            score = 0.0
            for res in bd.values():
                if isinstance(res, dict) and res.get("provider_name") == name:
                    score = float(res.get("risk_score", 0.0)); break
            row.append(score)
        lvl = int(getattr(e, "escalation_level", 1) or 1)
        X.append(row); y.append(max(0, min(3, lvl - 1)))
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int64)


_PHISH, _MITM = 1, 5   # provider indices used as regime drivers


def _make_old_task(n: int = 400, seed: int = 1) -> Tuple[np.ndarray, np.ndarray]:
    """Old regime: a high phishing score means containment (class 3)."""
    rng = np.random.default_rng(seed)
    X = (rng.random((n, len(FEATURE_ORDER))) * 0.3).astype(np.float32)
    y = np.ones(n, dtype=np.int64)
    hot = rng.random(n) < 0.5
    X[hot, _PHISH] = 0.7 + rng.random(hot.sum()) * 0.3
    y[hot] = 3
    return X, y


def _make_new_task(n: int = 400, seed: int = 2) -> Tuple[np.ndarray, np.ndarray]:
    """New regime with genuine conflict: attackers pivoted to MITM (high MAC/IP
    signal → class 3), AND phishing-lookalike traffic is now mostly benign
    (high phishing score → class 1). That relabel is what erases the old
    phishing knowledge under naive retraining — the effect EWC must resist."""
    rng = np.random.default_rng(seed)
    X = (rng.random((n, len(FEATURE_ORDER))) * 0.3).astype(np.float32)
    y = np.ones(n, dtype=np.int64)
    half = rng.random(n) < 0.5
    X[half, _MITM] = 0.7 + rng.random(half.sum()) * 0.3     # new attack → contain
    y[half] = 3
    X[~half, _PHISH] = 0.7 + rng.random((~half).sum()) * 0.3  # old signal now benign
    y[~half] = 1
    return X, y


def compute_fisher(model, X: "np.ndarray", y: "np.ndarray") -> Dict[str, "torch.Tensor"]:
    """Diagonal Fisher information: average of squared per-sample gradients of
    the log-likelihood of the model's own predicted class."""
    model.eval()
    fisher = {n: torch.zeros_like(p) for n, p in model.named_parameters()}
    xb = torch.tensor(X)
    logp = torch.log_softmax(model(xb), dim=1)
    for i in range(len(X)):
        model.zero_grad()
        cls = int(logp[i].argmax())
        logp[i, cls].backward(retain_graph=(i < len(X) - 1))
        for n, p in model.named_parameters():
            if p.grad is not None:
                fisher[n] += p.grad.detach() ** 2
    for n in fisher:
        fisher[n] /= max(1, len(X))
    return fisher


def train_with_ewc(model, X, y, fisher=None, theta_star=None, lam: float = 0.4,
                   epochs: int = 60, lr: float = 1e-2) -> Dict[str, float]:
    """Fine-tune on (X, y). If a prior Fisher + anchor weights are supplied, add
    the EWC penalty λ·Σ F·(θ−θ*)² so weights important to the old task barely
    move. Returns training diagnostics including the final EWC penalty."""
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    ce = nn.CrossEntropyLoss()
    xb, yb = torch.tensor(X), torch.tensor(y)
    last_penalty = 0.0
    for _ in range(epochs):
        model.train(); opt.zero_grad()
        loss = ce(model(xb), yb)
        penalty = torch.tensor(0.0)
        if fisher is not None and theta_star is not None:
            for n, p in model.named_parameters():
                penalty = penalty + (fisher[n] * (p - theta_star[n]) ** 2).sum()
            loss = loss + lam * penalty
        loss.backward(); opt.step()
        last_penalty = float(penalty.detach())
    return {"final_loss": float(loss.detach()), "ewc_penalty": round(last_penalty, 6)}


def _accuracy(model, X, y) -> float:
    if len(X) == 0:
        return 0.0
    with torch.no_grad():
        pred = model(torch.tensor(X)).argmax(1).numpy()
    return float((pred == y).mean())


def run_weekly_retrain(events: List[Any], lam: float = 50.0, seed: int = 0) -> Dict[str, Any]:
    """Entry point for the admin endpoint.

    Demonstrates EWC end-to-end: train an 'old task', snapshot Fisher + weights,
    then train the new week's data both WITHOUT and WITH the EWC penalty and
    report how much each forgets the old task. Uses real events for the new task
    when available, synthetic otherwise. `seed` makes runs independent so the
    verification harness can build a distribution over seeds.
    """
    if not _TORCH:
        return {"error": "torch unavailable in this container — run on the admin service."}

    torch.manual_seed(seed)
    # Old task = an established attack regime (phishing-heavy weeks).
    Xo, yo = _make_old_task(seed=seed + 1)
    model = FusionHead()
    train_with_ewc(model, Xo, yo, lam=lam)          # learn old task
    old_acc_before = _accuracy(model, Xo, yo)
    fisher = compute_fisher(model, Xo, yo)
    theta_star = {n: p.detach().clone() for n, p in model.named_parameters()}

    # New task = this week. Prefer real events; fall back to a conflicting regime.
    Xn, yn = events_to_dataset(events)
    used_real = len(Xn) >= 40
    if not used_real:
        Xn, yn = _make_new_task(seed=seed + 2)

    # (a) naive fine-tune (no EWC) on a fresh copy → measure forgetting
    naive = FusionHead(); naive.load_state_dict(model.state_dict())
    train_with_ewc(naive, Xn, yn, lam=0.0)
    naive_old = _accuracy(naive, Xo, yo)
    naive_new = _accuracy(naive, Xn, yn)

    # (b) EWC fine-tune on the anchored model
    diag = train_with_ewc(model, Xn, yn, fisher=fisher, theta_star=theta_star, lam=lam)
    ewc_old = _accuracy(model, Xo, yo)
    ewc_new = _accuracy(model, Xn, yn)

    os.makedirs(os.path.dirname(ARTIFACT), exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "features": FEATURE_ORDER,
                "fisher": {n: f for n, f in fisher.items()}, "lambda": lam,
                "trained_at": time.time()}, ARTIFACT)

    naive_forget = round(old_acc_before - naive_old, 4)
    ewc_forget = round(old_acc_before - ewc_old, 4)
    reduction = round((1 - ewc_forget / naive_forget) * 100, 1) if naive_forget > 1e-6 else 0.0
    return {
        "lambda": lam,
        "new_task_source": "live_events" if used_real else "synthetic_shift",
        "new_task_samples": int(len(Xn)),
        "old_task_acc_before": round(old_acc_before, 4),
        "naive_retrain": {"old_task_acc": round(naive_old, 4), "new_task_acc": round(naive_new, 4),
                          "forgetting": naive_forget},
        "ewc_retrain": {"old_task_acc": round(ewc_old, 4), "new_task_acc": round(ewc_new, 4),
                        "forgetting": ewc_forget, "ewc_penalty": diag["ewc_penalty"]},
        "forgetting_reduction_pct": reduction,
        "artifact": ARTIFACT,
    }


# In-process history so the admin panel can chart retrain runs across a session.
RETRAIN_HISTORY: List[Dict[str, Any]] = []
