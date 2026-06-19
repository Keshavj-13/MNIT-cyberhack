from sqlalchemy import Column, Integer, Float, String, JSON, DateTime, Boolean, create_engine, text, ForeignKey
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
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Banking simulator fields
    banking_id = Column(String(12), unique=True, index=True, nullable=True)
    balance = Column(Float, default=0.0)

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
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    receiver_banking_id = Column(String, index=True, nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    amount = Column(Float, nullable=False)
    status = Column(String, default="PENDING")  # PENDING, COMPLETED, FAILED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    amount = Column(Float, nullable=False)
    running_balance = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Beneficiary(Base):
    __tablename__ = "beneficiaries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    name = Column(String, nullable=False)
    account_number = Column(String, nullable=False)
    bank_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class RevokedToken(Base):
    __tablename__ = "revoked_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String, index=True, unique=True)
    revoked_at = Column(DateTime, default=datetime.datetime.utcnow)

# DB Session setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./security_platform.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_schema()

def _migrate_schema():
    """Add columns that existed in the ORM model but predate the live table."""
    migrations = {
        "security_events": [
            ("user_id", "ALTER TABLE security_events ADD COLUMN user_id VARCHAR DEFAULT 'ANONYMOUS'"),
            ("session_id", "ALTER TABLE security_events ADD COLUMN session_id VARCHAR DEFAULT 'DEFAULT'"),
            ("event_category", "ALTER TABLE security_events ADD COLUMN event_category VARCHAR DEFAULT 'NEUTRAL'"),
        ],
        "users": [
            ("banking_id", "ALTER TABLE users ADD COLUMN banking_id VARCHAR(12)"),
            ("balance", "ALTER TABLE users ADD COLUMN balance FLOAT DEFAULT 0.0"),
        ],
        "otp_verifications": [
            ("transaction_id", "ALTER TABLE otp_verifications ADD COLUMN transaction_id INTEGER"),
        ],
        "transactions": [
            ("sender_id", "ALTER TABLE transactions ADD COLUMN sender_id INTEGER DEFAULT 0"),
            ("receiver_banking_id", "ALTER TABLE transactions ADD COLUMN receiver_banking_id VARCHAR DEFAULT ''"),
            ("receiver_id", "ALTER TABLE transactions ADD COLUMN receiver_id INTEGER DEFAULT 0"),
            ("created_at", "ALTER TABLE transactions ADD COLUMN created_at DATETIME"),
            ("updated_at", "ALTER TABLE transactions ADD COLUMN updated_at DATETIME"),
        ]
    }
    with engine.connect() as conn:
        for table, cols in migrations.items():
            try:
                existing_cols = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
                for col, ddl in cols:
                    if col not in existing_cols:
                        conn.execute(text(ddl))
            except Exception:
                pass  # Table might not exist yet, create_all will handle it
        conn.commit()

