import json
from fastapi import FastAPI, Depends, HTTPException, Body, Security, Response, Cookie
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Tuple
import uvicorn
import secrets

from src.db.models import SessionLocal, init_db, TelemetryData, CustomerSession, SecurityEvent
from src.api.internal.session_crypto import (
    generate_aes_key, encrypt_aes_gcm, decrypt_aes_gcm,
    create_jwt_token, verify_jwt_token, JWT_SECRETS
)
from src.api.internal.evaluation_runner import run_evaluation

app = FastAPI(title="MNIT Customer Banking API", version="1.0.0")

# Strict CORS: Allow only Customer frontend port 3001
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Key-Version"],
)

# DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# JWT Token extractor helper
def get_current_user_payload(authorization: Optional[str] = Cookie(None, alias="customer_session"), db: Session = Depends(get_db)):
    if not authorization:
        # Fallback to Authorization header if cookies aren't set
        raise HTTPException(status_code=401, detail="Authentication session cookie required")
    return verify_jwt_token(authorization, "customer", db)

# Encrypted Request/Response Models
class EncryptedPayload(BaseModel):
    session_id: str
    key_version: int
    ciphertext: str
    nonce: str
    tag: str

# Helper to decrypt client payload
def decrypt_payload(payload: EncryptedPayload, db: Session) -> Tuple[Dict[str, Any], CustomerSession]:
    cust_session = db.query(CustomerSession).filter(
        CustomerSession.session_id == payload.session_id,
        CustomerSession.is_active == True
    ).first()
    
    if not cust_session:
        raise HTTPException(status_code=401, detail="Invalid, expired or inactive session key")
        
    if cust_session.key_version != payload.key_version:
        raise HTTPException(status_code=409, detail="Cryptographic key version mismatch: Key has been shuffled")
        
    try:
        decrypted_str = decrypt_aes_gcm(payload.ciphertext, payload.nonce, payload.tag, cust_session.aes_key)
        return json.loads(decrypted_str), cust_session
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Decryption failed: {str(e)}")

# Helper to encrypt response payload
def encrypt_response(data: Any, cust_session: CustomerSession) -> Dict[str, Any]:
    plaintext = json.dumps(data)
    encrypted = encrypt_aes_gcm(plaintext, cust_session.aes_key)
    return {
        "session_id": cust_session.session_id,
        "key_version": cust_session.key_version,
        "ciphertext": encrypted["ciphertext"],
        "nonce": encrypted["nonce"],
        "tag": encrypted["tag"]
    }

# Helper to handle key shuffling/rotation when risk level escalates
def shuffle_session_key(cust_session: CustomerSession, new_risk_level: int, db: Session) -> Tuple[str, int]:
    """Generates a new AES session key, increments key version, and updates risk level."""
    new_key = generate_aes_key()
    cust_session.aes_key = new_key
    cust_session.key_version += 1
    cust_session.risk_level = new_risk_level
    
    if new_risk_level >= 4:
        cust_session.is_active = False # Disable session completely on containment
        
    db.commit()
    return new_key, cust_session.key_version

from typing import Tuple

# --- Routes ---

@app.post("/customer/auth/login")
def login(payload: Dict[str, str] = Body(...), response: Response = Response(), db: Session = Depends(get_db)):
    username = payload.get("username", "customer_user")
    password = payload.get("password") # In demo, accept any password
    
    # Establish dynamic session
    session_id = f"cust_sess_{secrets.token_hex(8)}"
    aes_key = generate_aes_key()
    
    cust_session = CustomerSession(
        session_id=session_id,
        user_id=username,
        aes_key=aes_key,
        risk_level=1,
        key_version=1,
        is_active=True
    )
    db.add(cust_session)
    
    # Create signed customer JWT
    token = create_jwt_token(username, "customer", expires_in_minutes=30, extra_claims={"sid": session_id})
    db.commit()
    
    # Set Path-scoped HTTP-Only secure cookie
    response.set_cookie(
        key="customer_session",
        value=token,
        httponly=True,
        secure=False, # Set to True in production
        samesite="strict",
        path="/customer"
    )
    
    return {
        "status": "success",
        "username": username,
        "session_id": session_id,
        "aes_key": aes_key,
        "key_version": 1,
        "risk_level": 1
    }

@app.post("/customer/auth/logout")
def logout(user = Depends(get_current_user_payload), response: Response = Response(), db: Session = Depends(get_db)):
    session_id = user.get("sid")
    jti = user.get("jti")
    
    # Invalidate session in DB
    if session_id:
        cust_session = db.query(CustomerSession).filter(CustomerSession.session_id == session_id).first()
        if cust_session:
            cust_session.is_active = False
            
    # Blacklist JWT token
    if jti:
        from src.api.internal.session_crypto import revoke_token
        revoke_token(jti, db)
        
    db.commit()
    
    # Clear session cookie
    response.delete_cookie(key="customer_session", path="/customer")
    return {"status": "success", "message": "Successfully logged out."}

@app.get("/customer/auth/me")
def me(user = Depends(get_current_user_payload), db: Session = Depends(get_db)):
    session_id = user.get("sid")
    cust_session = db.query(CustomerSession).filter(CustomerSession.session_id == session_id).first()
    
    if not cust_session or not cust_session.is_active:
        raise HTTPException(status_code=401, detail="Session is inactive or has been rotated out")
        
    return {
        "user_id": user.get("sub"),
        "session_id": session_id,
        "risk_level": cust_session.risk_level,
        "key_version": cust_session.key_version
    }

# Mock Database for Banking Details
MOCK_ACCOUNTS = {
    "checking": {"account_number": "TR-98234827493", "routing_number": "121000248", "balance": 12450.84},
    "savings": {"account_number": "TR-10293847562", "routing_number": "121000248", "balance": 45102.10}
}

MOCK_TRANSACTIONS = [
    {"id": 1, "date": "2026-06-15T10:30:00", "description": "Grocery Store Checkout", "amount": -78.45, "type": "debit"},
    {"id": 2, "date": "2026-06-14T08:15:00", "description": "Monthly Salary Deposit", "amount": 3500.00, "type": "credit"},
    {"id": 3, "date": "2026-06-12T14:45:00", "description": "Electricity Utility Bill", "amount": -120.00, "type": "debit"},
    {"id": 4, "date": "2026-06-10T19:00:00", "description": "Online Bookstore Payment", "amount": -42.10, "type": "debit"},
]

MOCK_BENEFICIARIES = [
    {"id": 1, "name": "Alice Smith", "account_number": "TR-47392847293", "bank_name": "Garanti BBVA"},
    {"id": 2, "name": "Bob Johnson", "account_number": "TR-10293847583", "bank_name": "Isbank"}
]

@app.post("/customer/account")
def get_account_details(payload: EncryptedPayload = Body(...), user = Depends(get_current_user_payload), db: Session = Depends(get_db)):
    # Decrypt request parameters (none expected, but verify crypto)
    _, cust_session = decrypt_payload(payload, db)
    
    # Return encrypted accounts data
    return encrypt_response(MOCK_ACCOUNTS, cust_session)

@app.post("/customer/statements")
def get_statements(payload: EncryptedPayload = Body(...), user = Depends(get_current_user_payload), db: Session = Depends(get_db)):
    _, cust_session = decrypt_payload(payload, db)
    
    # Return encrypted transactions
    return encrypt_response(MOCK_TRANSACTIONS, cust_session)

@app.post("/customer/beneficiaries")
def get_beneficiaries(payload: EncryptedPayload = Body(...), user = Depends(get_current_user_payload), db: Session = Depends(get_db)):
    decrypted_body, cust_session = decrypt_payload(payload, db)
    
    # If it's a GET operation disguised as POST (decrypted_body is empty), return list
    # If it contains name/account/bank, add new beneficiary and run silent evaluation
    if decrypted_body and "name" in decrypted_body:
        name = decrypted_body["name"]
        account_number = decrypted_body["account_number"]
        bank_name = decrypted_body["bank_name"]
        
        # In-memory append for this session's context
        new_beneficiary = {
            "id": len(MOCK_BENEFICIARIES) + 1,
            "name": name,
            "account_number": account_number,
            "bank_name": bank_name
        }
        MOCK_BENEFICIARIES.append(new_beneficiary)
        
        # Trigger silent evaluation to see if adding payee is an anomaly
        eval_payload = {
            "user_id": user.get("sub"),
            "session_id": cust_session.session_id,
            "is_new_beneficiary": True,
            "beneficiary_name": name,
            "action": "add_beneficiary"
        }
        eval_result = run_evaluation(eval_payload, db)
        
        # Key rotation check
        key_rotated = False
        new_key = None
        new_version = cust_session.key_version
        
        if eval_result.escalation_level > cust_session.risk_level:
            # Shuffle keys!
            new_key, new_version = shuffle_session_key(cust_session, eval_result.escalation_level, db)
            key_rotated = True
            
        status_map = {1: "approved", 2: "challenged", 3: "restricted", 4: "blocked"}
        status_msg = status_map.get(eval_result.escalation_level, "approved")
        
        response_data = {
            "status": "success",
            "beneficiary": new_beneficiary,
            "transfer_status": status_msg,
            "key_rotated": key_rotated,
            "new_key": new_key,
            "new_key_version": new_version,
            "risk_level": eval_result.escalation_level
        }
        return encrypt_response(response_data, cust_session)
        
    return encrypt_response(MOCK_BENEFICIARIES, cust_session)

@app.post("/customer/transfer")
def transfer(payload: EncryptedPayload = Body(...), user = Depends(get_current_user_payload), db: Session = Depends(get_db)):
    decrypted_body, cust_session = decrypt_payload(payload, db)
    
    amount = decrypted_body.get("amount", 0.0)
    beneficiary_id = decrypted_body.get("beneficiary_id")
    is_new = decrypted_body.get("is_new_beneficiary", False)
    
    # Run evaluation
    eval_payload = {
        "user_id": user.get("sub"),
        "session_id": cust_session.session_id,
        "amount": amount,
        "is_new_beneficiary": is_new,
        "action": "transfer"
    }
    eval_result = run_evaluation(eval_payload, db)
    
    # Key rotation check
    key_rotated = False
    new_key = None
    new_version = cust_session.key_version
    
    if eval_result.escalation_level > cust_session.risk_level:
        # Shuffle keys!
        new_key, new_version = shuffle_session_key(cust_session, eval_result.escalation_level, db)
        key_rotated = True
        
    # Standardised response messages, absolutely no scores or internal metadata.
    if eval_result.escalation_level == 1:
        status = "approved"
        msg = "Transfer submitted successfully."
        # Update checking balance
        MOCK_ACCOUNTS["checking"]["balance"] -= amount
    elif eval_result.escalation_level == 2:
        status = "challenged"
        msg = "We need to verify this transfer. A Step-up Verification (OTP) code has been sent to your registered phone."
    elif eval_result.escalation_level == 3:
        status = "restricted"
        msg = "This transfer exceeds your current session cryptographic limits. Transfer restricted."
    else:
        status = "blocked"
        msg = "Security containment activated. Cryptographic session keys revoked. Access terminated."
        
    response_data = {
        "status": status,
        "message": msg,
        "key_rotated": key_rotated,
        "new_key": new_key,
        "new_key_version": new_version,
        "risk_level": eval_result.escalation_level
    }
    
    return encrypt_response(response_data, cust_session)

@app.post("/customer/telemetry")
def telemetry(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    # Telemetry comes in silently, optionally encrypted or standard JSON.
    # To ensure telemetry is never interrupted, if it has 'ciphertext' encrypt block, decrypt it.
    session_id = payload.get("session_id", "UNKNOWN")
    key_version = payload.get("key_version", 1)
    
    events = []
    if "ciphertext" in payload:
        cust_session = db.query(CustomerSession).filter(CustomerSession.session_id == session_id).first()
        if cust_session and cust_session.is_active:
            try:
                decrypted_str = decrypt_aes_gcm(payload["ciphertext"], payload["nonce"], payload["tag"], cust_session.aes_key)
                events = json.loads(decrypted_str).get("events", [])
            except Exception as e:
                print(f"[TELEMETRY ERROR] Decryption failed: {str(e)}")
                return {"status": "error", "message": "Telemetry decryption failed"}
    else:
        events = payload.get("events", [])
        
    for event in events:
        db_telemetry = TelemetryData(
            session_id=session_id,
            type=event.get("type"),
            data=event.get("data")
        )
        db.add(db_telemetry)
    
    db.commit()
    return {"status": "success", "count": len(events)}

if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="127.0.0.1", port=8001)
