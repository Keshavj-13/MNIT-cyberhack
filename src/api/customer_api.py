import json
import re
import os
import hashlib
import smtplib
import datetime
from email.message import EmailMessage
from fastapi import FastAPI, Depends, HTTPException, Body, Security, Response, Cookie, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Tuple
import uvicorn
import secrets

from src.db.models import SessionLocal, init_db, TelemetryData, CustomerSession, SecurityEvent, User, OTPVerification
from src.api.internal.session_crypto import (
    generate_aes_key, encrypt_aes_gcm, decrypt_aes_gcm,
    create_jwt_token, verify_jwt_token, JWT_SECRETS
)
from src.api.internal.evaluation_runner import run_evaluation

app = FastAPI(title="MNIT Customer Banking API", version="1.0.0")

@app.on_event("startup")
def on_startup():
    init_db()

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
def get_current_user_payload(
    authorization: Optional[str] = Cookie(None, alias="customer_session"),
    auth_header: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    token = None
    if auth_header:
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            token = auth_header
    if not token:
        token = authorization
            
    if not token:
        raise HTTPException(status_code=401, detail="Authentication session cookie or token required")
    return verify_jwt_token(token, "customer", db)

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
    new_key = generate_aes_key()
    cust_session.aes_key = new_key
    cust_session.key_version += 1
    cust_session.risk_level = new_risk_level
    if new_risk_level >= 4:
        cust_session.is_active = False
    db.commit()
    return new_key, cust_session.key_version

def maybe_deescalate(cust_session: CustomerSession, eval_result, db: Session):
    # step risk down one level if current eval is clean and session is elevated
    # ponytail: one-level step-down per clean event — avoids abrupt drops, no timer needed
    if cust_session.risk_level > 1 and eval_result.escalation_level == 1:
        cust_session.risk_level = max(1, cust_session.risk_level - 1)
        db.commit()

from typing import Tuple

# --- Password Validation ---

def validate_password(password: str) -> Tuple[bool, str]:
    """Enforce strong password policy: >=14 chars, upper, lower, digit, special."""
    if len(password) < 14:
        return False, "Password must be at least 14 characters long."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one digit."
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':\"\\|,.<>\/?`~]', password):
        return False, "Password must contain at least one special character."
    return True, "Password is strong."

import hmac as _hmac

def hash_password(password: str) -> str:
    # PBKDF2-SHA256 with random salt — resists rainbow tables unlike bare SHA-256
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 260000)
    return f"{salt}:{h.hex()}"

def verify_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split(':', 1)
        expected = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 260000)
        return _hmac.compare_digest(expected.hex(), h)
    except Exception:
        return False

def hash_otp(otp: str) -> str:
    # OTP space is only 1M values — high iteration count slows brute force
    salt = secrets.token_hex(8)
    h = hashlib.pbkdf2_hmac('sha256', otp.encode(), salt.encode(), 100000)
    return f"{salt}:{h.hex()}"

def verify_otp(otp: str, stored: str) -> bool:
    try:
        salt, h = stored.split(':', 1)
        expected = hashlib.pbkdf2_hmac('sha256', otp.encode(), salt.encode(), 100000)
        return _hmac.compare_digest(expected.hex(), h)
    except Exception:
        return False

# --- OTP Email Sending ---

def send_email_otp(to_email: str, otp_code: str):
    """Send OTP via SMTP. Falls back to console print if env vars are not set."""
    smtp_email = os.environ.get("SMTP_EMAIL")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    
    if not smtp_email or not smtp_password:
        print(f"[EMAIL OTP] To: {to_email} | Code: {otp_code}")
        return
    
    try:
        msg = EmailMessage()
        msg.set_content(
            f"Your Central Bank of India verification code is: {otp_code}\n\n"
            f"This code expires in 10 minutes. Do not share it with anyone."
        )
        msg['Subject'] = f'CBI Verification Code: {otp_code}'
        msg['From'] = smtp_email
        msg['To'] = to_email
        
        server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        server.login(smtp_email, smtp_password)
        server.send_message(msg)
        server.quit()
        print(f"[EMAIL OTP] Sent to {to_email}")
    except Exception as e:
        print(f"[EMAIL OTP ERROR] {str(e)} — Fallback: Code for {to_email} is {otp_code}")

def send_sms_otp(phone_number: str, otp_code: str):
    """Simulate SMS OTP delivery by printing to console."""
    print(f"[SMS OTP] To: {phone_number} | Code: {otp_code}")

# --- Auth Routes ---

@app.post("/customer/auth/register")
def register(payload: Dict[str, str] = Body(...), db: Session = Depends(get_db)):
    """Register a new customer account."""
    username = payload.get("username", "").strip()
    email = payload.get("email", "").strip().lower()
    phone = payload.get("phone", "").strip()
    password = payload.get("password", "")
    
    # Validate required fields
    if not username or not email or not phone or not password:
        raise HTTPException(status_code=400, detail="All fields (username, email, phone, password) are required.")
    
    # Validate username (alphanumeric + underscore, 3-30 chars)
    if not re.match(r'^[a-zA-Z0-9_]{3,30}$', username):
        raise HTTPException(status_code=400, detail="Username must be 3-30 characters, alphanumeric and underscores only.")
    
    # Validate email format
    if not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email):
        raise HTTPException(status_code=400, detail="Invalid email address format.")
    
    # Validate phone format (basic check for digits, 10-15 chars)
    phone_digits = re.sub(r'[^0-9]', '', phone)
    if len(phone_digits) < 10 or len(phone_digits) > 15:
        raise HTTPException(status_code=400, detail="Phone number must be 10-15 digits.")
    
    # Validate password strength
    is_valid, message = validate_password(password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)
    
    # Check uniqueness
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=409, detail="Username is already taken.")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email is already registered.")
    if db.query(User).filter(User.phone == phone).first():
        raise HTTPException(status_code=409, detail="Phone number is already registered.")
    
    # Create user
    user = User(
        username=username,
        email=email,
        phone=phone,
        password_hash=hash_password(password),
        email_verified=False,
        phone_verified=False,
        is_active=True
    )
    db.add(user)
    db.commit()
    
    return {
        "status": "success",
        "message": "Account created. Please verify your email and phone number.",
        "username": username,
        "email": email,
        "phone": phone
    }

@app.post("/customer/auth/send-otp")
def send_otp(payload: Dict[str, str] = Body(...), db: Session = Depends(get_db)):
    """Generate and send an OTP to email or phone."""
    identifier = payload.get("identifier", "").strip()
    channel = payload.get("channel", "").strip().lower()
    
    if not identifier or channel not in ("email", "phone"):
        raise HTTPException(status_code=400, detail="Valid identifier and channel (email/phone) required.")
    
    # Rate limit: check if there's a recent unexpired OTP for this identifier (within 60s)
    recent_otp = db.query(OTPVerification).filter(
        OTPVerification.identifier == identifier,
        OTPVerification.channel == channel,
        OTPVerification.is_used == False
    ).order_by(OTPVerification.created_at.desc()).first()
    
    if recent_otp:
        elapsed = (datetime.datetime.utcnow() - recent_otp.created_at).total_seconds()
        if elapsed < 60:
            raise HTTPException(status_code=429, detail=f"Please wait {int(60 - elapsed)} seconds before requesting a new code.")
    
    # Generate 6-digit OTP
    otp_code = str(secrets.SystemRandom().randint(100000, 999999))
    
    # Store hashed OTP
    otp_record = OTPVerification(
        identifier=identifier,
        otp_hash=hash_otp(otp_code),
        channel=channel,
        purpose="registration",
        attempts=0,
        is_used=False
    )
    db.add(otp_record)
    db.commit()
    
    # Send the OTP
    if channel == "email":
        send_email_otp(identifier, otp_code)
    else:
        send_sms_otp(identifier, otp_code)
    
    # Mask identifier for response
    if channel == "email":
        parts = identifier.split("@")
        masked = parts[0][:2] + "***@" + parts[1] if len(parts) == 2 else identifier
    else:
        masked = identifier[:3] + "****" + identifier[-4:] if len(identifier) > 7 else identifier
    
    res = {
        "status": "success",
        "message": f"Verification code sent to {masked}"
    }
    if os.environ.get("ALLOW_DEFAULT_SECRETS") == "1":
        res["dev_otp"] = otp_code
    return res

@app.post("/customer/auth/verify-otp")
def verify_otp_endpoint(payload: Dict[str, str] = Body(...), db: Session = Depends(get_db)):
    """Verify a submitted OTP code."""
    identifier = payload.get("identifier", "").strip()
    otp_code = payload.get("otp", "").strip()
    channel = payload.get("channel", "").strip().lower()
    
    if not identifier or not otp_code or channel not in ("email", "phone"):
        raise HTTPException(status_code=400, detail="Identifier, OTP code, and channel are required.")
    
    # Find the latest unused OTP for this identifier+channel
    otp_record = db.query(OTPVerification).filter(
        OTPVerification.identifier == identifier,
        OTPVerification.channel == channel,
        OTPVerification.is_used == False
    ).order_by(OTPVerification.created_at.desc()).first()
    
    if not otp_record:
        raise HTTPException(status_code=404, detail="No pending verification found. Please request a new code.")
    
    # Check expiry (10 minutes)
    elapsed = (datetime.datetime.utcnow() - otp_record.created_at).total_seconds()
    if elapsed > 600:
        otp_record.is_used = True
        db.commit()
        raise HTTPException(status_code=410, detail="Verification code has expired. Please request a new one.")
    
    # Check max attempts
    if otp_record.attempts >= 5:
        otp_record.is_used = True
        db.commit()
        raise HTTPException(status_code=429, detail="Too many incorrect attempts. Please request a new code.")
    
    # Verify hash
    if not verify_otp(otp_code, otp_record.otp_hash):
        otp_record.attempts += 1
        db.commit()
        remaining = 5 - otp_record.attempts
        raise HTTPException(status_code=400, detail=f"Invalid code. {remaining} attempt(s) remaining.")
    
    # Success — mark OTP as used
    otp_record.is_used = True
    db.commit()
    
    # Update the user's verification status
    if channel == "email":
        user = db.query(User).filter(User.email == identifier).first()
        if user:
            user.email_verified = True
            db.commit()
    elif channel == "phone":
        user = db.query(User).filter(User.phone == identifier).first()
        if user:
            user.phone_verified = True
            db.commit()
    
    return {
        "status": "success",
        "verified": True,
        "channel": channel,
        "message": f"{channel.capitalize()} verified successfully."
    }

@app.post("/customer/auth/login")
def login(payload: Dict[str, str] = Body(...), response: Response = Response(), db: Session = Depends(get_db)):
    """Authenticate a registered user and establish a cryptographic session."""
    username = payload.get("username", "").strip()
    password = payload.get("password", "")
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required.")
    
    # Look up user in DB
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    
    # Verify password hash
    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    
    # Check account is active
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account has been deactivated. Contact support.")
    
    # Check both email and phone are verified
    if not user.email_verified or not user.phone_verified:
        unverified = []
        if not user.email_verified:
            unverified.append("email")
        if not user.phone_verified:
            unverified.append("phone")
        raise HTTPException(
            status_code=403,
            detail=f"Account verification incomplete. Unverified: {', '.join(unverified)}. Please complete verification first."
        )
    
    # Check if the user's latest session is contained/locked out
    latest_sess = db.query(CustomerSession).filter(CustomerSession.user_id == username).order_by(CustomerSession.created_at.desc()).first()
    if latest_sess and latest_sess.risk_level >= 4:
        # Keep it contained, but generate a new token so they can run recovery
        latest_sess.is_active = True # Re-activate so token validation passes
        db.commit()
        
        token = create_jwt_token(username, "customer", expires_in_minutes=30, extra_claims={"sid": latest_sess.session_id})
        response.set_cookie(
            key="customer_session",
            value=token,
            httponly=True,
            secure=os.environ.get("SECURE_COOKIES", "false").lower() == "true",
            samesite="strict",
            path="/customer"
        )
        return {
            "status": "success",
            "username": username,
            "session_id": latest_sess.session_id,
            "aes_key": latest_sess.aes_key,
            "key_version": latest_sess.key_version,
            "risk_level": 4,
            "token": token
        }

    # Deactivate all previous sessions for this user so run-live always finds the right one
    db.query(CustomerSession).filter(
        CustomerSession.user_id == username,
        CustomerSession.is_active == True
    ).update({"is_active": False})
    db.commit()

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
        secure=os.environ.get("SECURE_COOKIES", "false").lower() == "true",
        samesite="strict",
        path="/customer"
    )
    
    return {
        "status": "success",
        "username": username,
        "session_id": session_id,
        "aes_key": aes_key,
        "key_version": 1,
        "risk_level": 1,
        "token": token
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
        "key_version": cust_session.key_version,
        "aes_key": cust_session.aes_key
    }

# Mock Database for Banking Details
_DEFAULT_ACCOUNTS = {
    "checking": {"account_number": "TR-98234827493", "routing_number": "121000248", "balance": 12450.84},
    "savings": {"account_number": "TR-10293847562", "routing_number": "121000248", "balance": 45102.10}
}

_DEFAULT_TRANSACTIONS = [
    {"id": 1, "date": "2026-06-15T10:30:00", "description": "Grocery Store Checkout", "amount": -78.45, "type": "debit"},
    {"id": 2, "date": "2026-06-14T08:15:00", "description": "Monthly Salary Deposit", "amount": 3500.00, "type": "credit"},
    {"id": 3, "date": "2026-06-12T14:45:00", "description": "Electricity Utility Bill", "amount": -120.00, "type": "debit"},
    {"id": 4, "date": "2026-06-10T19:00:00", "description": "Online Bookstore Payment", "amount": -42.10, "type": "debit"},
]

import copy
_USER_ACCOUNTS: Dict[str, dict] = {}
_USER_TRANSACTIONS: Dict[str, list] = {}

def _get_accounts(user_id: str) -> dict:
    if user_id not in _USER_ACCOUNTS:
        _USER_ACCOUNTS[user_id] = copy.deepcopy(_DEFAULT_ACCOUNTS)
    return _USER_ACCOUNTS[user_id]

def _get_transactions(user_id: str) -> list:
    if user_id not in _USER_TRANSACTIONS:
        _USER_TRANSACTIONS[user_id] = list(_DEFAULT_TRANSACTIONS)
    return _USER_TRANSACTIONS[user_id]

# ponytail: per-user lists, no DB table needed for mock data
_DEFAULT_BENEFICIARIES = [
    {"id": 1, "name": "Alice Smith", "account_number": "TR-47392847293", "bank_name": "Garanti BBVA"},
    {"id": 2, "name": "Bob Johnson", "account_number": "TR-10293847583", "bank_name": "Isbank"}
]
_USER_BENEFICIARIES: Dict[str, list] = {}

def _get_beneficiaries(user_id: str) -> list:
    if user_id not in _USER_BENEFICIARIES:
        _USER_BENEFICIARIES[user_id] = list(_DEFAULT_BENEFICIARIES)
    return _USER_BENEFICIARIES[user_id]

@app.post("/customer/account")
def get_account_details(payload: EncryptedPayload = Body(...), user = Depends(get_current_user_payload), db: Session = Depends(get_db)):
    # Decrypt request parameters (none expected, but verify crypto)
    _, cust_session = decrypt_payload(payload, db)
    uid = user.get("sub", "")
    
    # Return encrypted accounts data
    return encrypt_response(_get_accounts(uid), cust_session)

@app.post("/customer/statements")
def get_statements(payload: EncryptedPayload = Body(...), user = Depends(get_current_user_payload), db: Session = Depends(get_db)):
    _, cust_session = decrypt_payload(payload, db)
    uid = user.get("sub", "")
    
    # Return encrypted transactions
    return encrypt_response(_get_transactions(uid), cust_session)

@app.post("/customer/beneficiaries")
def get_beneficiaries(payload: EncryptedPayload = Body(...), user = Depends(get_current_user_payload), db: Session = Depends(get_db)):
    decrypted_body, cust_session = decrypt_payload(payload, db)
    
    # If it's a GET operation disguised as POST (decrypted_body is empty), return list
    # If it contains name/account/bank, add new beneficiary and run silent evaluation
    uid = user.get("sub", "")
    blist = _get_beneficiaries(uid)
    if decrypted_body and "name" in decrypted_body:
        name = decrypted_body.get("name", "").strip()
        account_number = decrypted_body.get("account_number", "").strip()
        bank_name = decrypted_body.get("bank_name", "").strip()
        if not name or len(name) > 100 or not account_number or len(account_number) > 50:
            raise HTTPException(status_code=400, detail="Invalid beneficiary fields.")
        new_beneficiary = {"id": len(blist) + 1, "name": name, "account_number": account_number, "bank_name": bank_name}
        blist.append(new_beneficiary)
        
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
        
        maybe_deescalate(cust_session, eval_result, db)
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
    return encrypt_response(blist, cust_session)

@app.post("/customer/transfer")
def transfer(payload: EncryptedPayload = Body(...), user = Depends(get_current_user_payload), db: Session = Depends(get_db)):
    decrypted_body, cust_session = decrypt_payload(payload, db)
    
    try:
        amount = float(decrypted_body.get("amount", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid transfer amount.")
    if amount <= 0 or amount > 1_000_000:
        raise HTTPException(status_code=400, detail="Amount must be between 0 and 1,000,000.")
    beneficiary_id = decrypted_body.get("beneficiary_id")
    uid = user.get("sub", "")
    if beneficiary_id is not None and not any(str(b["id"]) == str(beneficiary_id) for b in _get_beneficiaries(uid)):
        raise HTTPException(status_code=400, detail="Beneficiary not found.")
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
        
        # Determine beneficiary name
        b_name = "Unknown Transfer"
        if beneficiary_id is not None:
            found = next((b for b in _get_beneficiaries(uid) if str(b["id"]) == str(beneficiary_id)), None)
            if found:
                b_name = found.get("name", "Unknown Transfer")
                
        # Update checking balance
        user_accounts = _get_accounts(uid)
        user_accounts["checking"]["balance"] -= amount
        
        # Append transaction to ledger
        user_tx = _get_transactions(uid)
        new_tx = {
            "id": len(user_tx) + 1,
            "date": datetime.utcnow().isoformat(),
            "description": f"Transfer to {b_name}",
            "amount": -amount,
            "type": "debit"
        }
        user_tx.insert(0, new_tx) # Add to the top of the ledger
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
    session_id = payload.get("session_id", "")
    # reject telemetry from unknown/inactive sessions to prevent score injection
    cust_session = db.query(CustomerSession).filter(
        CustomerSession.session_id == session_id, CustomerSession.is_active == True
    ).first()
    if not cust_session:
        raise HTTPException(status_code=401, detail="Invalid or inactive session")

    events = []
    if "ciphertext" in payload:
        try:
            decrypted_str = decrypt_aes_gcm(payload["ciphertext"], payload["nonce"], payload["tag"], cust_session.aes_key)
            events = json.loads(decrypted_str).get("events", [])
        except Exception as e:
            return {"status": "error", "message": "Telemetry decryption failed"}
    else:
        events = payload.get("events", [])

    for event in events:
        client_ts = event.get("timestamp")
        dt_ts = None
        if client_ts:
            try:
                dt_ts = datetime.datetime.fromtimestamp(client_ts / 1000.0, datetime.timezone.utc).replace(tzinfo=None)
            except Exception:
                pass
        db.add(TelemetryData(
            session_id=session_id,
            type=event.get("type"),
            timestamp=dt_ts,
            data=event.get("data")
        ))
    db.commit()
    return {"status": "success", "count": len(events)}

@app.get("/customer/auth/recovery-card")
def get_recovery_card_route(user = Depends(get_current_user_payload), db: Session = Depends(get_db)):
    import base64
    db_user = db.query(User).filter(User.username == user.get("sub")).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not db_user.recovery_card_data:
        from src.api.internal.recovery_card import generate_card
        db_user.recovery_card_data = generate_card()
        db.commit()
        
    from src.api.internal.recovery_card import render_card_png
    card_bytes = render_card_png(db_user.recovery_card_data, db_user.username)
    
    is_svg = b"<svg" in card_bytes
    content_type = "image/svg+xml" if is_svg else "image/png"
    card_base64 = base64.b64encode(card_bytes).decode("utf-8")
    
    return {
        "content_type": content_type,
        "card_base64": card_base64
    }

if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="127.0.0.1", port=8001)
