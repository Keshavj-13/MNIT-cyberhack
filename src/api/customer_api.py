import json
import re
import os
import hashlib
import smtplib
import datetime
from email.message import EmailMessage
from fastapi import FastAPI, Depends, HTTPException, Body, Security, Response, Cookie
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Tuple
import uvicorn
import secrets

from src.db.models import SessionLocal, init_db, TelemetryData, CustomerSession, SecurityEvent, User, OTPVerification, Transaction, LedgerEntry, Beneficiary
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

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode('utf-8')).hexdigest()

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
        
    # Generate unique banking_id
    sys_rand = secrets.SystemRandom()
    while True:
        random_digits = "".join([str(sys_rand.randint(0, 9)) for _ in range(8)])
        banking_id = f"CBI-{random_digits}"
        if not db.query(User).filter(User.banking_id == banking_id).first():
            break
            
    # Generate random initial balance (e.g., between 500.00 and 50000.00)
    initial_balance = round(sys_rand.uniform(500.0, 50000.0), 2)
    
    # Create user
    user = User(
        username=username,
        email=email,
        phone=phone,
        password_hash=hash_password(password),
        email_verified=False,
        phone_verified=False,
        is_active=True,
        banking_id=banking_id,
        balance=initial_balance
    )
    db.add(user)
    db.commit()
    
    return {
        "status": "success",
        "message": "Account created. Please verify your email and phone number.",
        "username": username,
        "email": email,
        "phone": phone,
        "banking_id": banking_id,
        "balance": initial_balance
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
    
    return {
        "status": "success",
        "message": f"Verification code sent to {masked}"
    }

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
    if hash_otp(otp_code) != otp_record.otp_hash:
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
    if user.password_hash != hash_password(password):
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
    
    # Establish dynamic cryptographic session (existing logic preserved)
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

@app.post("/customer/account")
def get_account_details(payload: EncryptedPayload = Body(...), user_payload = Depends(get_current_user_payload), db: Session = Depends(get_db)):
    _, cust_session = decrypt_payload(payload, db)
    
    username = user_payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    accounts = {
        "checking": {
            "account_number": user.banking_id,
            "routing_number": "121000248",
            "balance": user.balance
        },
        "savings": {
            "account_number": user.banking_id,
            "routing_number": "121000248",
            "balance": 0.0
        }
    }
    
    return encrypt_response(accounts, cust_session)

@app.post("/customer/statements")
def get_statements(payload: EncryptedPayload = Body(...), user_payload = Depends(get_current_user_payload), db: Session = Depends(get_db)):
    _, cust_session = decrypt_payload(payload, db)
    
    username = user_payload.get("sub")
    db_user = db.query(User).filter(User.username == username).first()
    
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    ledger_entries = db.query(LedgerEntry).filter(
        LedgerEntry.user_id == db_user.id
    ).order_by(LedgerEntry.created_at.desc()).limit(50).all()
    
    transactions = []
    for entry in ledger_entries:
        transactions.append({
            "id": entry.id,
            "date": entry.created_at.isoformat(),
            "description": entry.description or "Transaction",
            "amount": entry.amount,
            "type": "credit" if entry.amount > 0 else "debit",
            "running_balance": entry.running_balance
        })
        
    return encrypt_response(transactions, cust_session)

@app.post("/customer/beneficiaries")
def manage_beneficiaries(payload: EncryptedPayload = Body(...), user_payload = Depends(get_current_user_payload), db: Session = Depends(get_db)):
    decrypted_body, cust_session = decrypt_payload(payload, db)
    
    username = user_payload.get("sub")
    db_user = db.query(User).filter(User.username == username).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if decrypted_body and "name" in decrypted_body:
        # Add new beneficiary
        name = decrypted_body.get("name")
        account_number = decrypted_body.get("account_number")
        bank_name = decrypted_body.get("bank_name")
        
        new_beneficiary = Beneficiary(
            user_id=db_user.id,
            name=name,
            account_number=account_number,
            bank_name=bank_name
        )
        db.add(new_beneficiary)
        db.commit()
        db.refresh(new_beneficiary)
        
        eval_payload = {
            "user_id": username,
            "session_id": cust_session.session_id,
            "is_new_beneficiary": True,
            "beneficiary_name": name,
            "action": "add_beneficiary"
        }
        eval_result = run_evaluation(eval_payload, db)
        
        key_rotated = False
        new_key = None
        new_version = cust_session.key_version
        
        if eval_result.escalation_level > cust_session.risk_level:
            new_key, new_version = shuffle_session_key(cust_session, eval_result.escalation_level, db)
            key_rotated = True
            
        status_map = {1: "approved", 2: "challenged", 3: "restricted", 4: "blocked"}
        status_msg = status_map.get(eval_result.escalation_level, "approved")
        
        response_data = {
            "status": "success",
            "beneficiary": {
                "id": new_beneficiary.id,
                "name": new_beneficiary.name,
                "account_number": new_beneficiary.account_number,
                "bank_name": new_beneficiary.bank_name
            },
            "transfer_status": status_msg,
            "key_rotated": key_rotated,
            "new_key": new_key,
            "new_key_version": new_version,
            "risk_level": eval_result.escalation_level
        }
        return encrypt_response(response_data, cust_session)
        
    # Return list of beneficiaries
    beneficiaries = db.query(Beneficiary).filter(Beneficiary.user_id == db_user.id).all()
    bene_list = [
        {"id": b.id, "name": b.name, "account_number": b.account_number, "bank_name": b.bank_name}
        for b in beneficiaries
    ]
    
    return encrypt_response(bene_list, cust_session)

@app.post("/customer/transfer/initiate")
def initiate_transfer(payload: EncryptedPayload = Body(...), user_payload = Depends(get_current_user_payload), db: Session = Depends(get_db)):
    decrypted_body, cust_session = decrypt_payload(payload, db)
    
    amount = float(decrypted_body.get("amount", 0.0))
    target_banking_id = decrypted_body.get("target_banking_id", "").strip()
    password = decrypted_body.get("password", "")
    
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Transfer amount must be greater than zero.")
        
    sender_username = user_payload.get("sub")
    sender = db.query(User).filter(User.username == sender_username).first()
    
    if not sender:
        raise HTTPException(status_code=404, detail="Sender not found.")
        
    # Verify password
    if sender.password_hash != hash_password(password):
        raise HTTPException(status_code=401, detail="Invalid password.")
        
    # Verify balance
    if sender.balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient funds.")
        
    # Look up target receiver
    receiver = db.query(User).filter(User.banking_id == target_banking_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="Beneficiary Banking ID not found.")
    
    if sender.id == receiver.id:
        raise HTTPException(status_code=400, detail="Cannot transfer funds to yourself.")
        
    # Optional Threat Evaluation
    eval_payload = {
        "user_id": sender_username,
        "session_id": cust_session.session_id,
        "amount": amount,
        "is_new_beneficiary": True,
        "action": "transfer_initiate"
    }
    eval_result = run_evaluation(eval_payload, db)
    
    # Key rotation check
    key_rotated = False
    new_key = None
    new_version = cust_session.key_version
    if eval_result.escalation_level > cust_session.risk_level:
        new_key, new_version = shuffle_session_key(cust_session, eval_result.escalation_level, db)
        key_rotated = True

    if eval_result.escalation_level >= 3:
        raise HTTPException(status_code=403, detail="Security containment activated. Transfer restricted.")
    
    # Create PENDING Transaction
    tx = Transaction(
        sender_id=sender.id,
        receiver_banking_id=target_banking_id,
        receiver_id=receiver.id,
        amount=amount,
        status="PENDING"
    )
    db.add(tx)
    db.commit()
    
    # Generate OTP
    otp_code = str(secrets.SystemRandom().randint(100000, 999999))
    otp_record = OTPVerification(
        identifier=sender.email,
        otp_hash=hash_otp(otp_code),
        channel="email",
        purpose="transfer",
        transaction_id=tx.id,
        attempts=0,
        is_used=False
    )
    db.add(otp_record)
    db.commit()
    
    # Send Email OTP
    send_email_otp(sender.email, otp_code)
    
    response_data = {
        "status": "success",
        "message": "Transfer initiated. Step-up Verification (OTP) code sent to your registered email.",
        "transaction_id": tx.id,
        "key_rotated": key_rotated,
        "new_key": new_key,
        "new_key_version": new_version,
        "risk_level": eval_result.escalation_level
    }
    
    return encrypt_response(response_data, cust_session)

@app.post("/customer/transfer/confirm")
def confirm_transfer(payload: EncryptedPayload = Body(...), user_payload = Depends(get_current_user_payload), db: Session = Depends(get_db)):
    decrypted_body, cust_session = decrypt_payload(payload, db)
    
    transaction_id = decrypted_body.get("transaction_id")
    otp_code = decrypted_body.get("otp", "").strip()
    
    if not transaction_id or not otp_code:
        raise HTTPException(status_code=400, detail="Transaction ID and OTP are required.")
        
    sender_username = user_payload.get("sub")
    sender = db.query(User).filter(User.username == sender_username).first()
    
    # Find PENDING transaction
    tx = db.query(Transaction).filter(
        Transaction.id == transaction_id, 
        Transaction.sender_id == sender.id,
        Transaction.status == "PENDING"
    ).first()
    
    if not tx:
        raise HTTPException(status_code=404, detail="Pending transaction not found or already processed.")
        
    # Verify OTP
    otp_record = db.query(OTPVerification).filter(
        OTPVerification.transaction_id == tx.id,
        OTPVerification.identifier == sender.email,
        OTPVerification.purpose == "transfer",
        OTPVerification.is_used == False
    ).order_by(OTPVerification.created_at.desc()).first()
    
    if not otp_record:
        raise HTTPException(status_code=404, detail="No pending verification found for this transaction.")
        
    # Check expiry (10 mins)
    elapsed = (datetime.datetime.utcnow() - otp_record.created_at).total_seconds()
    if elapsed > 600:
        otp_record.is_used = True
        tx.status = "FAILED"
        db.commit()
        raise HTTPException(status_code=410, detail="Verification code expired. Transfer cancelled.")
        
    if otp_record.attempts >= 5:
        otp_record.is_used = True
        tx.status = "FAILED"
        db.commit()
        raise HTTPException(status_code=429, detail="Too many incorrect attempts. Transfer cancelled.")
        
    if hash_otp(otp_code) != otp_record.otp_hash:
        otp_record.attempts += 1
        db.commit()
        remaining = 5 - otp_record.attempts
        raise HTTPException(status_code=400, detail=f"Invalid code. {remaining} attempt(s) remaining.")
        
    # OTP Valid -> Execute Transfer
    otp_record.is_used = True
    tx.status = "COMPLETED"
    
    receiver = db.query(User).filter(User.id == tx.receiver_id).first()
    
    sender.balance -= tx.amount
    receiver.balance += tx.amount
    
    # Ledger Entries
    sender_ledger = LedgerEntry(
        transaction_id=tx.id,
        user_id=sender.id,
        amount=-tx.amount,
        running_balance=sender.balance,
        description=f"Transfer to CBI ID: {receiver.banking_id}"
    )
    
    receiver_ledger = LedgerEntry(
        transaction_id=tx.id,
        user_id=receiver.id,
        amount=tx.amount,
        running_balance=receiver.balance,
        description=f"Transfer from CBI ID: {sender.banking_id}"
    )
    
    db.add(sender_ledger)
    db.add(receiver_ledger)
    db.commit()
    
    response_data = {
        "status": "success",
        "message": "Transfer completed successfully."
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
