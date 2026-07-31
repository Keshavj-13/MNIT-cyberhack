"""Exhaustive truth-table: real build_reasoning == independent spec, ALL inputs.

The Z3 proofs (verification/smt) prove properties of a MODEL of the classifier.
This test closes the loop: it runs the ACTUAL build_reasoning over the entire
meaningful finite partition of the input space and checks it against an
independent reference (spec_classify). Green here means the code and the proven
model agree everywhere — no drift between what we proved and what runs.
"""
import itertools
import pytest

from src.explainability.concept_bottleneck import build_reasoning
from verification.props.reasoning_fixtures import (
    make_result, make_payload, spec_classify,
    FLAG_COMBOS, URL_POINTS, BEH_POINTS, TIERS,
)

CASES = list(itertools.product(FLAG_COMBOS, URL_POINTS, BEH_POINTS, TIERS))


@pytest.mark.parametrize("flags,url,beh,tier", CASES)
def test_reasoning_matches_spec(flags, url, beh, tier):
    ip, mac, oem = flags
    result = make_result(ip, mac, oem, url, beh, tier)
    payload = make_payload(ip, mac, oem)
    out = build_reasoning(result, payload)

    exp_attack, exp_crypto = spec_classify(ip, mac, oem, url, beh, tier)
    assert out["attack_type"] == exp_attack, (
        f"attack mismatch for ip={ip} mac={mac} oem={oem} url={url} beh={beh} tier={tier}: "
        f"got {out['attack_type']}, spec {exp_attack}")
    assert out["crypto_action"] == exp_crypto
    assert out["tier_response"] == tier
    assert 0.0 <= out["confidence"] <= 1.0


def test_space_is_exhaustive():
    # 8 flag combos × 3 url × 2 beh × 4 tier — guards against silently shrinking the grid.
    assert len(CASES) == 8 * 3 * 2 * 4 == 192
