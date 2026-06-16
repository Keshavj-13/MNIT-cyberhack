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
    """Add columns that existed in the ORM model but predate the live table.

    Base.metadata.create_all() only creates missing tables, it never alters
    existing ones. security_events was created before user_id/session_id/
    event_category were added to the ORM model, so those columns are missing
    from older databases and every /evaluate call fails with
    'no such column: security_events.user_id'.
    """
    migrations = {
        "user_id": "ALTER TABLE security_events ADD COLUMN user_id VARCHAR DEFAULT 'ANONYMOUS'",
        "session_id": "ALTER TABLE security_events ADD COLUMN session_id VARCHAR DEFAULT 'DEFAULT'",
        "event_category": "ALTER TABLE security_events ADD COLUMN event_category VARCHAR DEFAULT 'NEUTRAL'",
    }
    with engine.connect() as conn:
        existing_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(security_events)"))}
        for col, ddl in migrations.items():
            if col not in existing_cols:
                conn.execute(text(ddl))
        conn.commit()

