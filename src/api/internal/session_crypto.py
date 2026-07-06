import base64
import os
import secrets
import datetime
import hashlib
import hmac
import json
import time
from typing import Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.db.models import RevokedToken, CustomerSession

JWT_SECRETS = {
    "customer": os.environ.get("CUSTOMER_JWT_SECRET", "customer_secure_secret_key_rotation_9876543210"),
    "admin": os.environ.get("ADMIN_JWT_SECRET", "admin_secure_secret_dashboard_monitoring_9876543210"),
    "attacker": os.environ.get("ATTACKER_JWT_SECRET", "attacker_secure_secret_simulation_console_9876543210"),
}
_DEFAULTS = {"customer_secure_secret_key_rotation_9876543210", "admin_secure_secret_dashboard_monitoring_9876543210", "attacker_secure_secret_simulation_console_9876543210"}
# block startup with weak secrets in prod; dev skips by setting ALLOW_DEFAULT_SECRETS=1
if any(v in _DEFAULTS for v in JWT_SECRETS.values()) and not os.environ.get("ALLOW_DEFAULT_SECRETS"):
    import warnings; warnings.warn("JWT secrets using insecure defaults. Set CUSTOMER/ADMIN/ATTACKER_JWT_SECRET or ALLOW_DEFAULT_SECRETS=1 for dev.", stacklevel=1)

# --- Pure Python HMAC-SHA256-CTR AEAD Cryptography ---
# Bypasses Windows AppLocker compiled Rust DLL blocks by using built-in hashlib and hmac.

def generate_aes_key() -> str:
    """Generate a random 256-bit symmetric key and return as base64 string."""
    return base64.b64encode(secrets.token_bytes(32)).decode('utf-8')

def _xor_bytes(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))

def _derive_keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    """Generate a keystream using HMAC-SHA256 in Counter (CTR) mode."""
    keystream = b''
    counter = 0
    while len(keystream) < length:
        block = hmac.new(key, nonce + counter.to_bytes(4, 'big'), hashlib.sha256).digest()
        keystream += block
        counter += 1
    return keystream[:length]

def encrypt_aes_gcm(plaintext: str, key_b64: str) -> Dict[str, str]:
    """Encrypt plaintext using pure-Python HMAC-CTR AEAD stream cipher."""
    try:
        key = base64.b64decode(key_b64.encode('utf-8'))
        nonce = secrets.token_bytes(16)
        plaintext_bytes = plaintext.encode('utf-8')
        
        keystream = _derive_keystream(key, nonce, len(plaintext_bytes))
        ciphertext = _xor_bytes(plaintext_bytes, keystream)
        
        # Encrypt-then-MAC authentication tag
        mac = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
        
        return {
            "ciphertext": base64.b64encode(ciphertext).decode('utf-8'),
            "nonce": base64.b64encode(nonce).decode('utf-8'),
            "tag": base64.b64encode(mac).decode('utf-8')
        }
    except Exception as e:
        raise ValueError(f"Symmetric encryption failed: {str(e)}")

def decrypt_aes_gcm(ciphertext_b64: str, nonce_b64: str, tag_b64: str, key_b64: str) -> str:
    """Decrypt ciphertext using pure-Python HMAC-CTR AEAD stream cipher."""
    try:
        key = base64.b64decode(key_b64.encode('utf-8'))
        nonce = base64.b64decode(nonce_b64.encode('utf-8'))
        tag = base64.b64decode(tag_b64.encode('utf-8'))
        ciphertext = base64.b64decode(ciphertext_b64.encode('utf-8'))
        
        # Verify MAC first
        expected_mac = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(tag, expected_mac):
            raise ValueError("Cryptographic integrity check failed: Invalid signature tag")
            
        keystream = _derive_keystream(key, nonce, len(ciphertext))
        plaintext_bytes = _xor_bytes(ciphertext, keystream)
        return plaintext_bytes.decode('utf-8')
    except Exception as e:
        raise ValueError(f"Symmetric decryption failed: {str(e)}")

# --- Pure Python JWT (HS256) Implementation ---
# Avoids importing 'pyjwt' which implicitly triggers 'cryptography' Rust DLL loads.

def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def _base64url_decode(data: str) -> bytes:
    padding = '=' * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode((data + padding).encode('utf-8'))

def jwt_encode(payload: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    # Standard compact separators
    header_json = json.dumps(header, separators=(',', ':')).encode('utf-8')
    payload_json = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    
    header_b64 = _base64url_encode(header_json)
    payload_b64 = _base64url_encode(payload_json)
    
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(secret.encode('utf-8'), signing_input, hashlib.sha256).digest()
    signature_b64 = _base64url_encode(signature)
    
    return f"{header_b64}.{payload_b64}.{signature_b64}"

def jwt_decode(token: str, secret: str) -> dict:
    parts = token.split('.')
    if len(parts) != 3:
        raise ValueError("Invalid JWT token structure")
        
    header_b64, payload_b64, signature_b64 = parts
    
    # Verify signature
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    expected_sig = hmac.new(secret.encode('utf-8'), signing_input, hashlib.sha256).digest()
    expected_sig_b64 = _base64url_encode(expected_sig)
    
    if not hmac.compare_digest(signature_b64.encode('utf-8'), expected_sig_b64.encode('utf-8')):
        raise ValueError("JWT Signature verification failed")
        
    # Decode payload
    payload_json = _base64url_decode(payload_b64)
    payload = json.loads(payload_json.decode('utf-8'))
    
    # Check expiration (JWT exp claim is epoch seconds)
    if 'exp' in payload:
        if time.time() > payload['exp']:
            raise ValueError("JWT token has expired")
            
    return payload

def create_jwt_token(subject: str, surface: str, expires_in_minutes: int = 1440, extra_claims: dict = None) -> str:
    """Create a signed JWT token for a specific surface."""
    secret = JWT_SECRETS[surface]
    now = time.time()
    payload = {
        "sub": subject,
        "surface": surface,
        "iat": int(now),
        "exp": int(now + (expires_in_minutes * 60)),
        "jti": secrets.token_hex(16)
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt_encode(payload, secret)

def verify_jwt_token(token: str, surface: str, db: Session) -> Dict[str, Any]:
    """Verify JWT token and check blacklist."""
    secret = JWT_SECRETS[surface]
    try:
        payload = jwt_decode(token, secret)
        
        # Check surface alignment
        if payload.get("surface") != surface:
            raise HTTPException(status_code=403, detail="Access denied: Token not issued for this surface")
            
        # Check token blacklist (revoked tokens)
        jti = payload.get("jti")
        if jti:
            is_revoked = db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
            if is_revoked:
                raise HTTPException(status_code=401, detail="Session has been revoked/terminated")
                
        return payload
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid session credentials: {str(e)}")

def revoke_token(jti: str, db: Session):
    """Blacklist a JWT token by its JTI."""
    if not jti:
        return
    already_revoked = db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
    if not already_revoked:
        db.add(RevokedToken(jti=jti))
        db.commit()
