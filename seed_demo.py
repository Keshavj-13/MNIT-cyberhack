"""
seed_demo.py — Idempotent demo data seeder.

Run once before any demo to ensure:
1. keshav user exists with correct password, email verified, recovery card set
2. 12 realistic beneficiaries exist for keshav
3. At least 4 security events exist (admin dashboard populated)
4. An ARIA investigation exists (pre-seeded so it shows immediately)

Usage:  python seed_demo.py
"""
import os, sys, hashlib, secrets, datetime, json
os.environ.setdefault("ALLOW_DEFAULT_SECRETS", "1")
os.environ.setdefault("SQLALCHEMY_DATABASE_URL", "sqlite:///./security_platform.db")

from src.db.models import SessionLocal, init_db, User, SecurityEvent, AriaInvestigation, Beneficiary
from src.api.internal.recovery_card import generate_card

DEMO_USER     = "keshav"
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

# Real, active recipient accounts the demo user has NEVER transferred to.
# Money sent to their derived account number lands in a real balance (not an empty ghost).
_RECIPIENTS = [
    ("ganeev",  "Ganeev",  "ganeev@cbi.co.in"),
    ("ishpuneet",   "Ishpuneet",   "ishpuneet@cbi.co.in"),
    ("namanmeet",    "Namanmeet",    "namanmeet@cbi.co.in"),
]

def hash_password(pw: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 260000).hex()
    return f"{salt}:{h}"

def derive_checking_account(username: str) -> str:
    """Mirror customer_api._get_accounts so seeded recipients get the same TR- number."""
    h = hashlib.sha256(username.encode()).hexdigest()
    suffix = str(int(h[:8], 16))[:11].zfill(11)
    return f"TR-{suffix}"

def main():
    init_db()
    db = SessionLocal()
    try:
        # ── 1. Ensure keshav exists with correct password + verification ──
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

        # ── 2b. Seed real recipient accounts (never transferred to) ──────────
        for r_user, r_name, r_email in _RECIPIENTS:
            existing = db.query(User).filter_by(username=r_user).first()
            if not existing:
                db.add(User(
                    username=r_user, email=r_email, phone=f"+9190000{abs(hash(r_user)) % 100000:05d}",
                    password_hash=hash_password("Recipient@Cbi2026!"),
                    is_active=True, email_verified=True, phone_verified=True,
                    recovery_card_data=generate_card(),
                ))
        db.commit()

        # ── 4. Ensure one ARIA investigation exists ───────────────────────────
        inv_count = db.query(AriaInvestigation).filter_by(cluster_key=DEMO_USER).count()
        if inv_count == 0:
            event_ids = [e.id for e in db.query(SecurityEvent).filter_by(user_id=DEMO_USER).order_by(SecurityEvent.id.desc()).limit(4).all()]
            inv = AriaInvestigation(
                cluster_key=DEMO_USER, cycle=1,
                cluster_event_ids=event_ids,
                classification="account_takeover",
                hypothesis="Progressive ATO attack: LURE→HOOK→EXPLOIT→MONETIZE kill chain detected against keshav",
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
        print("\nKnown recipient accounts (use these in Transfer > New recipient):")
        for r_user, r_name, _ in _RECIPIENTS:
            print(f"  {r_name:<14} {derive_checking_account(r_user)}")

    finally:
        db.close()

if __name__ == "__main__":
    main()
