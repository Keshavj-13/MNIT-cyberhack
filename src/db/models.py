from sqlalchemy import Column, Integer, Float, String, JSON, DateTime, Boolean, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()

class SecurityEvent(Base):
    __tablename__ = "security_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    session_id = Column(String, index=True)
    event_category = Column(String, default="NEUTRAL") # LURE, HOOK, EXPLOIT, MONETIZE
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    input_payload = Column(JSON)
    overall_risk = Column(Float)
    decision = Column(String)
    escalation_level = Column(Integer)
    confidence = Column(Float)
    breakdown = Column(JSON)
    recommendation = Column(String)
    why_decision = Column(String)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    action = Column(String)
    details = Column(String)

class TelemetryData(Base):
    __tablename__ = "telemetry_data"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    type = Column(String) # keystroke, mouse, session
    data = Column(JSON)

class CustomerSession(Base):
    __tablename__ = "customer_sessions"
    
    session_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    aes_key = Column(String)  # Base64 encoded AES-256 key
    risk_level = Column(Integer, default=1)
    key_version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_ghost = Column(Boolean, default=False)           # non-loginable recipient account
    recovery_card_data = Column(JSON, nullable=True)    # {A1:7, B3:2, ...} for Tier 4
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class OTPVerification(Base):
    __tablename__ = "otp_verifications"
    
    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String, index=True, nullable=False)  # email or phone
    otp_hash = Column(String, nullable=False)  # SHA-256 hash of the 6-digit code
    channel = Column(String, nullable=False)  # "email" or "phone"
    purpose = Column(String, default="registration")  # "registration", "login_challenge"
    attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_used = Column(Boolean, default=False)

class AriaInvestigation(Base):
    __tablename__ = "aria_investigations"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    cluster_key = Column(String, index=True)          # user_id being investigated
    cluster_event_ids = Column(JSON)                  # [int, ...]
    cycle = Column(Integer, default=1)                # how many ARIA passes touched this
    hypothesis = Column(String)
    classification = Column(String)                   # social_eng_chain, ato_fraud, coordinated, unknown
    evidence_summary = Column(String)
    vlm_assessment = Column(String)                   # Qwen's visual analysis
    confidence = Column(Float, default=0.0)
    status = Column(String, default="open")           # open / resolved / fp_confirmed

class Beneficiary(Base):
    """Per-user saved beneficiaries — persisted so they survive API restarts."""
    __tablename__ = "beneficiaries"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    account_number = Column(String, nullable=False)
    bank_name = Column(String, nullable=False)
    is_ghost = Column(Boolean, default=False)   # auto-created ghost recipient
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class RevokedToken(Base):
    __tablename__ = "revoked_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String, index=True, unique=True)
    revoked_at = Column(DateTime, default=datetime.datetime.utcnow)

# DB Session setup
import os as _os
SQLALCHEMY_DATABASE_URL = _os.environ.get("SQLALCHEMY_DATABASE_URL", "sqlite:///./security_platform.db")
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_schema()

def _migrate_schema():
    """Add columns that existed in the ORM model but predate the live table.

    Base.metadata.create_all() only creates missing tables, it never alters
    existing ones. security_events was created before user_id/session_id/
    event_category were added to the ORM model, so those columns are missing
    from older databases and every /evaluate call fails with
    'no such column: security_events.user_id'.
    """
    migrations = {
        "security_events": {
            "user_id": "ALTER TABLE security_events ADD COLUMN user_id VARCHAR DEFAULT 'ANONYMOUS'",
            "session_id": "ALTER TABLE security_events ADD COLUMN session_id VARCHAR DEFAULT 'DEFAULT'",
            "event_category": "ALTER TABLE security_events ADD COLUMN event_category VARCHAR DEFAULT 'NEUTRAL'",
        },
        "users": {
            "is_ghost": "ALTER TABLE users ADD COLUMN is_ghost BOOLEAN DEFAULT 0",
            "recovery_card_data": "ALTER TABLE users ADD COLUMN recovery_card_data JSON",
        },
    }
    with engine.connect() as conn:
        for table, cols in migrations.items():
            existing_cols = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            for col, ddl in cols.items():
                if col not in existing_cols:
                    try:
                        conn.execute(text(ddl))
                    except Exception:
                        pass
        conn.commit()

