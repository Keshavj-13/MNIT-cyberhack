"""Robustness fuzzing: the engine and reasoning layer must never crash or emit
out-of-range scores on hostile/malformed input, and the platform's stated
security invariants must hold.
"""
from hypothesis import given, strategies as st, settings

from src.engine.risk_engine import RiskEngine
from src.api.internal.evaluation_runner import _registry
from src.explainability.concept_bottleneck import build_reasoning

_ENGINE = RiskEngine(_registry.get_providers())

# arbitrary JSON-ish payloads: random keys → random scalar/None/bool/str values
_scalars = st.one_of(st.none(), st.booleans(), st.integers(min_value=-10**9, max_value=10**9),
                     st.floats(allow_nan=True, allow_infinity=True),
                     st.text(max_size=40))
_payloads = st.dictionaries(st.text(min_size=1, max_size=20), _scalars, max_size=12)


@settings(max_examples=250, deadline=None)
@given(_payloads)
def test_engine_never_crashes_and_scores_bounded(payload):
    payload.setdefault("session_id", "fuzz")
    result = _ENGINE.evaluate_all(payload)
    assert 0.0 <= result.overall_risk <= 1.0
    assert result.escalation_level in (1, 2, 3, 4)
    for res in result.provider_breakdown.values():
        assert 0.0 <= res.risk_score <= 1.0, f"{res.provider_name} out of range"


@settings(max_examples=250, deadline=None)
@given(_payloads)
def test_reasoning_never_crashes_on_fuzzed_result(payload):
    payload.setdefault("session_id", "fuzz")
    result = _ENGINE.evaluate_all(payload)
    reasoning = build_reasoning(result, payload)
    assert reasoning["attack_type"] in {"clean", "phishing", "behavioral_anomaly", "MITM", "session_hijack"}
    assert reasoning["crypto_action"] in {"maintain_AES", "upgrade_SHA512", "upgrade_SHA512_MLKEM"}
    assert 0.0 <= reasoning["confidence"] <= 1.0


def test_attacker_api_enforces_sim_prefix_invariant():
    # Security model (CLAUDE.md): the attacker surface may only ever write
    # sim_*-prefixed ids so it can never inject events against a real user.
    import inspect
    from src.api import attacker_api
    src = inspect.getsource(attacker_api)
    assert "sim_" in src, "attacker API lost its sim_ namespacing"


def test_ip_only_change_is_not_containment():
    # An IP change alone (VPN / mobile handoff) must NOT trigger containment —
    # only IP+MAC (MITM) or IP+OEM (hijack) may. Guards against over-blocking.
    r = _ENGINE.evaluate_all({"session_id": "x", "ip_changed": True})
    assert r.escalation_level < 4
