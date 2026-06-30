"""
seed_demo.py — Idempotent demo data seeder.

Run once before any demo to ensure:
1. demo_keshav user exists with correct password, email verified, recovery card set
2. 12 realistic beneficiaries exist for demo_keshav
3. At least 4 security events exist (admin dashboard populated)
4. An ARIA investigation exists (pre-seeded so it shows immediately)

Usage:  python seed_demo.py
"""
import os, sys, hashlib, secrets, datetime, json
os.environ.setdefault("ALLOW_DEFAULT_SECRETS", "1")
os.environ.setdefault("SQLALCHEMY_DATABASE_URL", "sqlite:///./security_platform.db")

from src.db.models import SessionLocal, init_db, User, SecurityEvent, AriaInvestigation, Beneficiary
from src.api.internal.recovery_card import generate_card

DEMO_USER     = "demo_keshav"
DEMO_PASSWORD = "DemoPass@Mnit2026!"
DEMO_EMAIL    = "demo@mnit.ac.in"
DEMO_PHONE    = "+919876543210"

_BENEFICIARIES = [
    ("Priya Sharma",       "CBI-10023847561", "Central Bank of India"),
    ("Rajesh Gupta",       "CBI-20034958672", "State Bank of India"),
    ("Ananya Verma",       "CBI-30045069783", "HDFC Bank"),
    ("Vikram Singh",       "CBI-40056170894", "ICICI Bank"),
    ("Sunita Patel",       "CBI-50067281905", "Punjab National Bank"),
    ("Arjun Mehta",        "CBI-60078392016", "Axis Bank"),
    ("Kavya Nair",         "CBI-70089403127", "Kotak Mahindra Bank"),
    ("Rohit Agarwal",      "CBI-80090514238", "Bank of Baroda"),
    ("Deepa Krishnan",     "CBI-90001625349", "Canara Bank"),
    ("Sanjay Yadav",       "CBI-11012736450", "Union Bank of India"),
    ("Pooja Bhatt",        "CBI-12023847561", "Indian Bank"),
    ("Amit Joshi",         "CBI-13034958672", "Bank of India"),
]

def hash_password(pw: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 260000).hex()
    return f"{salt}:{h}"

def main():
    init_db()
    db = SessionLocal()
    try:
        # ── 1. Ensure demo_keshav exists with correct password + verification ──
        user = db.query(User).filter_by(username=DEMO_USER).first()
        if not user:
            card = generate_card()
            user = User(
                username=DEMO_USER, email=DEMO_EMAIL, phone=DEMO_PHONE,
                password_hash=hash_password(DEMO_PASSWORD),
                is_active=True, email_verified=True, phone_verified=True,
                recovery_card_data=card,
            )
            db.add(user)
            print(f"  Created user: {DEMO_USER}")
        else:
            user.password_hash = hash_password(DEMO_PASSWORD)
            user.is_active = True
            user.email_verified = True
            user.phone_verified = True
            if not user.recovery_card_data:
                user.recovery_card_data = generate_card()
                print(f"  Generated recovery card for {DEMO_USER}")
            print(f"  Reset password + verified: {DEMO_USER}")
        db.commit()

        card_preview = list(user.recovery_card_data.items())[:4]
        print(f"  Recovery card preview: {card_preview} ...")

        # ── 2. Seed 12 beneficiaries ─────────────────────────────────────────
        existing_bens = db.query(Beneficiary).filter_by(user_id=DEMO_USER).count()
        if existing_bens < len(_BENEFICIARIES):
            existing_names = {b.name for b in db.query(Beneficiary).filter_by(user_id=DEMO_USER).all()}
            added = 0
            for name, acct, bank in _BENEFICIARIES:
                if name not in existing_names:
                    db.add(Beneficiary(
                        user_id=DEMO_USER, name=name,
                        account_number=acct, bank_name=bank, is_ghost=False
                    ))
                    added += 1
            db.commit()
            print(f"  Added {added} beneficiaries for {DEMO_USER}")
        else:
            print(f"  Beneficiaries already seeded ({existing_bens}) — skipping")

        # ── 3. Ensure at least 4 demo security events exist ──────────────────
        existing = db.query(SecurityEvent).filter_by(user_id=DEMO_USER).count()
        if existing < 4:
            now = datetime.datetime.utcnow()
            sample_events = [
                dict(overall_risk=0.08, decision="MONITOR", escalation_level=1, confidence=0.82,
                     event_category="NEUTRAL",
                     why_decision="Baseline session — normal keystroke cadence, no anomaly indicators.",
                     recommendation="No action required.",
                     breakdown={"BeaconBehavioralProvider":{"risk_score":0.05,"explanations":["Behaviour matches enrolled profile"]},"AccountTakeoverProvider":{"risk_score":0.08,"explanations":["Keystroke timing within normal range"]},"TransactionRiskProvider":{"risk_score":0.10,"explanations":["Low-value routine transaction"]},"NetworkRiskProvider":{"risk_score":0.02,"explanations":["Known residential IP"]},"DeviceTrustProvider":{"risk_score":0.00,"explanations":["Trusted device fingerprint"]},"SocialEngineeringRiskProvider":{"risk_score":0.01,"explanations":["URL matches known banking domain"]}},
                     timestamp=now - datetime.timedelta(minutes=8)),
                dict(overall_risk=0.41, decision="CHALLENGE", escalation_level=2, confidence=0.77,
                     event_category="HOOK",
                     why_decision="Behavioral drift detected. Keystroke cadence deviates from enrolled profile. BEACON cosine similarity below threshold.",
                     recommendation="Require OTP step-up verification before processing transfer.",
                     breakdown={"BeaconBehavioralProvider":{"risk_score":0.68,"explanations":["Cosine similarity 0.941 — below 0.980 threshold"]},"AccountTakeoverProvider":{"risk_score":0.45,"explanations":["IET variance elevated vs baseline"]},"TransactionRiskProvider":{"risk_score":0.35,"explanations":["New beneficiary added before transfer"]},"NetworkRiskProvider":{"risk_score":0.05,"explanations":["Same IP, no geo anomaly"]},"DeviceTrustProvider":{"risk_score":0.00,"explanations":["Same device"]},"SocialEngineeringRiskProvider":{"risk_score":0.02,"explanations":["No phishing indicators"]}},
                     timestamp=now - datetime.timedelta(minutes=5)),
                dict(overall_risk=0.63, decision="RESTRICT", escalation_level=3, confidence=0.88,
                     event_category="EXPLOIT",
                     why_decision="Sustained behavioral drift across multiple evaluation cycles. ATO distance exceeds threshold. Large transfer to new beneficiary attempted.",
                     recommendation="Block high-value transfers. Rotate session key. Require password reset.",
                     breakdown={"BeaconBehavioralProvider":{"risk_score":0.84,"explanations":["Cosine similarity 0.912 — severe drift"]},"AccountTakeoverProvider":{"risk_score":0.71,"explanations":["Keystroke pattern inconsistent with enrolled user"]},"TransactionRiskProvider":{"risk_score":0.65,"explanations":["High-value transfer to unverified beneficiary"]},"NetworkRiskProvider":{"risk_score":0.12,"explanations":["Minor geolocation variance"]},"DeviceTrustProvider":{"risk_score":0.00,"explanations":["Device unchanged"]},"SocialEngineeringRiskProvider":{"risk_score":0.08,"explanations":["URL legitimate"]}},
                     timestamp=now - datetime.timedelta(minutes=3)),
                dict(overall_risk=0.97, decision="CONTAIN", escalation_level=4, confidence=0.94,
                     event_category="MONETIZE",
                     why_decision="Containment threshold exceeded. BEACON drift critical (0.889). ATO confidence 94%. Large fraudulent transfer attempted. Session revoked.",
                     recommendation="Revoke session. Lock account. Require OTP + Recovery Card identity confirmation.",
                     breakdown={"BeaconBehavioralProvider":{"risk_score":0.97,"explanations":["Cosine similarity 0.889 — attacker cadence confirmed"]},"AccountTakeoverProvider":{"risk_score":0.94,"explanations":["Mahalanobis distance 4.2σ from enrolled baseline"]},"TransactionRiskProvider":{"risk_score":0.98,"explanations":["Maximum-value transfer to new unverified beneficiary"]},"NetworkRiskProvider":{"risk_score":0.31,"explanations":["IP flagged in threat intelligence feed"]},"DeviceTrustProvider":{"risk_score":0.05,"explanations":["Slight user-agent variance"]},"SocialEngineeringRiskProvider":{"risk_score":0.10,"explanations":["Redirect attempt to lookalike domain"]}},
                     timestamp=now - datetime.timedelta(minutes=1)),
            ]
            for ev in sample_events:
                ts = ev.pop("timestamp")
                se = SecurityEvent(
                    user_id=DEMO_USER, session_id="cust_sess_demo0001",
                    input_payload={"wpm": 47, "avg_dwell": 85, "avg_flight": 12, "mouse_velocity": 2.1, "error_rate": 0.02},
                    **ev, timestamp=ts
                )
                db.add(se)
            db.commit()
            print(f"  Seeded 4 demo events for {DEMO_USER}")
        else:
            print(f"  Events already exist ({existing}) — skipping seed")

        # ── 4. Ensure one ARIA investigation exists ───────────────────────────
        inv_count = db.query(AriaInvestigation).filter_by(cluster_key=DEMO_USER).count()
        if inv_count == 0:
            event_ids = [e.id for e in db.query(SecurityEvent).filter_by(user_id=DEMO_USER).order_by(SecurityEvent.id.desc()).limit(4).all()]
            inv = AriaInvestigation(
                cluster_key=DEMO_USER, cycle=1,
                cluster_event_ids=event_ids,
                classification="account_takeover",
                hypothesis="Progressive ATO attack: LURE→HOOK→EXPLOIT→MONETIZE kill chain detected against demo_keshav",
                evidence_summary="BEACON cosine similarity degraded from 0.99 (baseline) to 0.889 over 4 events. ATO distance reached 4.2σ. Transaction risk escalated with each step. Matches known ATO playbook.",
                confidence=0.91, status="open",
                vlm_assessment="ARIA has identified a 4-stage Account Takeover attack chain. The behavioral fingerprint (BEACON VarCNN) shows systematic degradation consistent with a human attacker gradually adapting their typing cadence. The transaction risk escalation pattern (low→high value, unknown beneficiary) confirms monetization intent. Recommended action: containment executed. Require customer OTP + Recovery Card identity confirmation before account reactivation.",
                created_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=1),
            )
            db.add(inv)
            db.commit()
            print(f"  Seeded ARIA investigation for {DEMO_USER}")
        else:
            print(f"  ARIA investigation already exists ({inv_count}) — skipping")

        print("\nDemo seed complete.")
        print(f"  Login:     {DEMO_USER} / {DEMO_PASSWORD}")
        print(f"  Email:     {DEMO_EMAIL} (verified)")
        print(f"  Card:      {list(user.recovery_card_data.items())[:6]}")

    finally:
        db.close()

if __name__ == "__main__":
    main()
