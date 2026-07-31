"""Statistical validation of the EWC continual learner.

Learning can't be *proved*, so we validate it the way ML results should be:
across many seeds with a significance test, plus a numerical check that the
Fisher information (which the whole method rests on) is actually correct. With
seeds pinned these are deterministic pass/fail gates, but the CLAIM they support
is statistical — "EWC forgets significantly less than naive retraining," not a
theorem.
"""
import math
import statistics
import pytest

torch = pytest.importorskip("torch")
from src.training.continual_learner import (
    run_weekly_retrain, compute_fisher, FusionHead, _make_old_task,
)

N_SEEDS = 20


@pytest.fixture(scope="module")
def runs():
    return [run_weekly_retrain([], lam=50.0, seed=s) for s in range(N_SEEDS)]


def _mean_ci(xs):
    m = statistics.mean(xs)
    if len(xs) < 2:
        return m, 0.0
    sd = statistics.stdev(xs)
    half = 1.96 * sd / math.sqrt(len(xs))     # 95% CI (normal approx)
    return m, half


def test_ewc_forgets_less_than_naive_on_average(runs):
    naive = [r["naive_retrain"]["forgetting"] for r in runs]
    ewc = [r["ewc_retrain"]["forgetting"] for r in runs]
    nm, nci = _mean_ci(naive)
    em, eci = _mean_ci(ewc)
    # EWC mean forgetting is clearly below naive, and the CIs don't touch.
    assert em < nm, f"EWC forgetting {em:.3f} not below naive {nm:.3f}"
    assert (em + eci) < (nm - nci), f"CIs overlap: ewc {em:.3f}±{eci:.3f} vs naive {nm:.3f}±{nci:.3f}"


def test_paired_reduction_significant(runs):
    # Paired sign test: EWC must beat naive on the large majority of seeds.
    diffs = [r["naive_retrain"]["forgetting"] - r["ewc_retrain"]["forgetting"] for r in runs]
    wins = sum(1 for d in diffs if d > 0)
    assert wins >= int(0.9 * len(diffs)), f"EWC only helped on {wins}/{len(diffs)} seeds"
    mean_reduction = statistics.mean(diffs)
    assert mean_reduction > 0.15, f"mean absolute forgetting reduction {mean_reduction:.3f} too small"


def test_plasticity_retained(runs):
    # Guard the stability–plasticity trade-off: EWC must still LEARN the new task,
    # not just freeze. This catches an over-large lambda that kills adaptation.
    new_acc = statistics.mean(r["ewc_retrain"]["new_task_acc"] for r in runs)
    assert new_acc >= 0.55, f"EWC new-task accuracy {new_acc:.3f} — lambda too rigid"


def test_determinism_same_seed():
    a = run_weekly_retrain([], lam=50.0, seed=7)
    b = run_weekly_retrain([], lam=50.0, seed=7)
    assert a["ewc_retrain"] == b["ewc_retrain"], "same seed produced different results"


def test_fisher_nonnegative():
    torch.manual_seed(0)
    Xo, yo = _make_old_task()
    model = FusionHead()
    fisher = compute_fisher(model, Xo, yo)
    for name, f in fisher.items():
        assert (f >= 0).all(), f"Fisher has negative entries in {name} (must be squares)"


def test_fisher_gradient_matches_finite_difference():
    """The Fisher diagonal is E[(d log p / d theta)^2]. Verify the underlying
    gradient (autograd) matches a central finite difference — a wrong gradient
    would silently make the EWC penalty meaningless."""
    torch.manual_seed(0)
    Xo, _ = _make_old_task(n=1)
    model = FusionHead().double()
    x = torch.tensor(Xo, dtype=torch.float64)

    def logp_cls():
        lp = torch.log_softmax(model(x), dim=1)
        return lp[0, int(lp[0].argmax())]

    model.zero_grad()
    logp_cls().backward()
    p = next(model.parameters())            # first weight matrix
    g_analytic = p.grad[0, 0].item()

    eps = 1e-6
    with torch.no_grad():
        p[0, 0] += eps
    f_plus = logp_cls().item()
    with torch.no_grad():
        p[0, 0] -= 2 * eps
    f_minus = logp_cls().item()
    g_fd = (f_plus - f_minus) / (2 * eps)

    assert abs(g_analytic - g_fd) < 1e-4, f"autograd {g_analytic:.6f} vs finite-diff {g_fd:.6f}"
