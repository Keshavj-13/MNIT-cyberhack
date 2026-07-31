"""End-to-end: drive real attacker scenarios through the production evaluation
pipeline (FeatureExtractor → RiskEngine → providers → reasoning → key rotation)
and assert the whole chain behaves. This is the integration counterpart to the
unit/formal layers: it exercises the code paths the demo actually runs.

Uses the live DB with a unique throwaway session id, cleaned up after each test.
"""
import uuid
import pytest

from src.db.models import SessionLocal, init_db, CustomerSession, SecurityEvent, TelemetryData
from src.api.internal.session_crypto import generate_aes_key
from src.api.internal.evaluation_runner import run_evaluation
from src.api.customer_api import shuffle_session_key
from src.api.attacker_api import DEMO_SCENARIOS

REASONING_KEYS = {"attack_type", "confidence", "triggered_concepts",
                  "tier_response", "crypto_action", "summary"}


@pytest.fixture()
def session():
    init_db()
    db = SessionLocal()
    sid = f"verif_{uuid.uuid4().hex[:12]}"
    uid = f"verif_user_{sid}"
    db.add(CustomerSession(session_id=sid, user_id=uid, aes_key=generate_aes_key(),
                           risk_level=1, key_version=1, is_active=True))
    db.commit()
    yield db, sid, uid
    for model in (SecurityEvent, TelemetryData):
        db.query(model).filter(model.session_id == sid).delete()
    db.query(CustomerSession).filter(CustomerSession.session_id == sid).delete()
    db.commit(); db.close()


def _run_scenario(db, sid, uid, name):
    """Replay a DEMO_SCENARIOS scenario; return (final EngineResult, final reasoning, session)."""
    final_result = final_reason = None
    for step in DEMO_SCENARIOS[name]:
        payload = {**step["payload"], "user_id": uid, "session_id": sid}
        if "url" in step["payload"]:
            payload["current_url"] = step["payload"]["url"]
        result = run_evaluation(payload, db)
        sess = db.query(CustomerSession).filter(CustomerSession.session_id == sid).first()
        if result.escalation_level > sess.risk_level:
            shuffle_session_key(sess, result.escalation_level, db)
        last = db.query(SecurityEvent).filter(SecurityEvent.session_id == sid)\
                 .order_by(SecurityEvent.id.desc()).first()
        final_result = result
        final_reason = (last.breakdown or {}).get("beacon_reasoning")
    return final_result, final_reason


def test_reasoning_persisted_with_full_contract(session):
    db, sid, uid = session
    _, reason = _run_scenario(db, sid, uid, "normal_customer")
    assert reason is not None
    assert REASONING_KEYS.issubset(reason.keys())


def test_mitm_scenario_contains_and_goes_pqc(session):
    db, sid, uid = session
    result, reason = _run_scenario(db, sid, uid, "mitm_intercept")
    assert result.escalation_level == 4
    assert reason["attack_type"] == "MITM"
    assert reason["crypto_action"] == "upgrade_SHA512_MLKEM"
    sess = db.query(CustomerSession).filter(CustomerSession.session_id == sid).first()
    assert sess.crypto_scheme == "X-Wing (X25519 + ML-KEM-768)"
    assert sess.is_active is False
    assert sess.crypto_descriptor.get("mlkem_ct_prefix")


def test_session_hijack_scenario_classified(session):
    db, sid, uid = session
    result, reason = _run_scenario(db, sid, uid, "session_hijack")
    assert result.escalation_level == 4
    assert reason["attack_type"] == "session_hijack"


def test_normal_customer_stays_low(session):
    db, sid, uid = session
    result, reason = _run_scenario(db, sid, uid, "normal_customer")
    assert result.escalation_level <= 2
    assert reason["attack_type"] == "clean"


def test_fingerprint_enrolls_before_flagging(session):
    # First sight of an IP/MAC must ENROLL (not flag) — otherwise every new
    # session would false-positive as a hijack.
    db, sid, uid = session
    r1 = run_evaluation({"user_id": uid, "session_id": sid,
                         "client_ip": "10.0.0.9", "device_mac": "a4:c3:f0:11:22:33"}, db)
    assert r1.escalation_level == 1
    sess = db.query(CustomerSession).filter(CustomerSession.session_id == sid).first()
    assert sess.enrolled_ip == "10.0.0.9"
    # Same fingerprint next event → still clean.
    r2 = run_evaluation({"user_id": uid, "session_id": sid,
                         "client_ip": "10.0.0.9", "device_mac": "a4:c3:f0:11:22:33"}, db)
    assert r2.escalation_level == 1
