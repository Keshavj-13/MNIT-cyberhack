"""Metamorphic property tests (Hypothesis) for the reasoning layer.

Where the truth-table checks fixed points and Z3 proves the model, these check
*relational* invariants — how the output must change (or not) as inputs change.
Hypothesis searches thousands of randomized inputs for a violation.
"""
from hypothesis import given, strategies as st

from src.explainability.concept_bottleneck import build_reasoning
from verification.props.reasoning_fixtures import make_result, make_payload

_SEVERITY = {"clean": 0, "phishing": 2, "behavioral_anomaly": 3, "MITM": 4, "session_hijack": 5}

flags = st.tuples(st.booleans(), st.booleans(), st.booleans())
url = st.floats(min_value=0, max_value=100)
beh = st.floats(min_value=0, max_value=1)
tier = st.integers(min_value=1, max_value=4)


def _reason(ip, mac, oem, u, b, t):
    return build_reasoning(make_result(ip, mac, oem, u, b, t), make_payload(ip, mac, oem))


@given(flags, url, beh, tier)
def test_confidence_in_unit_interval(f, u, b, t):
    out = _reason(*f, u, b, t)
    assert 0.0 <= out["confidence"] <= 1.0


@given(flags, url, beh, tier)
def test_tier1_always_clean(f, u, b, t):
    out = _reason(*f, u, b, 1)  # force tier 1
    assert out["attack_type"] == "clean"


@given(flags, url, beh, tier)
def test_crypto_action_tracks_tier(f, u, b, t):
    out = _reason(*f, u, b, t)
    expect = {1: "maintain_AES", 2: "maintain_AES", 3: "upgrade_SHA512", 4: "upgrade_SHA512_MLKEM"}[t]
    assert out["crypto_action"] == expect


@given(flags, url, beh)
def test_adding_oem_never_lowers_severity(f, u, b):
    # metamorphic: turning on the OEM-mismatch signal (device spoof) must never
    # DOWNgrade the attack severity, at any tier>=2.
    ip, mac, _ = f
    lo = _reason(ip, mac, False, u, b, 3)
    hi = _reason(ip, mac, True, u, b, 3)
    assert _SEVERITY[hi["attack_type"]] >= _SEVERITY[lo["attack_type"]]


@given(flags, beh, tier)
def test_raising_phishing_never_lowers_severity(f, b, t):
    ip, mac, oem = f
    lo = _reason(ip, mac, oem, 0.0, b, t)
    hi = _reason(ip, mac, oem, 95.0, b, t)
    assert _SEVERITY[hi["attack_type"]] >= _SEVERITY[lo["attack_type"]]


@given(flags, url, beh, tier)
def test_concepts_subset_of_fired_signals(f, u, b, t):
    # every triggered concept must correspond to a signal that is actually on
    out = _reason(*f, u, b, t)
    ip, mac, oem = f
    text = " ".join(out["triggered_concepts"])
    if "ip_changed" in text:
        assert ip
    if "mac_oem_mismatch" in text:
        assert oem
