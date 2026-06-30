# 5. Database & Security

---

## 5.1 Database Schema (`src/db/models.py`)

The platform uses SQLite (file: `security_platform.db`) via SQLAlchemy ORM. The database URL is configurable via the `SQLALCHEMY_DATABASE_URL` environment variable.

### Tables

#### `security_events` — Risk evaluation audit trail

| Column | Type | Purpose |
|--------|------|---------|
| `id` | Integer PK | Auto-increment |
| `user_id` | String (indexed) | User who triggered the evaluation |
| `session_id` | String (indexed) | Cryptographic session this event belongs to |
| `event_category` | String | Kill-chain stage: `LURE`, `HOOK`, `EXPLOIT`, `MONETIZE`, or `NEUTRAL` |
| `timestamp` | DateTime (indexed) | UTC timestamp of evaluation |
| `input_payload` | JSON | Raw input data sent to the risk engine |
| `overall_risk` | Float | Final fused risk score (0.0–1.0) |
| `decision` | String | `ALLOW`, `CHALLENGE`, `RESTRICT`, or `CONTAIN` |
| `escalation_level` | Integer | 1–4 security tier |
| `confidence` | Float | Weighted provider confidence |
| `breakdown` | JSON | Per-provider `{name: {risk_score, confidence, explanations, ...}}` |
| `recommendation` | String | Human-readable recommended action |
| `why_decision` | String | Explanation string, includes crypto rotation annotations |

#### `telemetry_data` — Raw behavioral telemetry

| Column | Type | Purpose |
|--------|------|---------|
| `id` | Integer PK | Auto-increment |
| `session_id` | String (indexed) | Links to the customer session |
| `timestamp` | DateTime | Client-provided timestamp (converted from epoch ms) |
| `type` | String | `keystroke`, `mouse`, or `session` |
| `data` | JSON | Event-specific payload (dwellTime, velocity, URL, etc.) |

#### `customer_sessions` — Cryptographic session state

| Column | Type | Purpose |
|--------|------|---------|
| `session_id` | String PK | Format: `cust_sess_{hex}` |
| `user_id` | String (indexed) | Username this session belongs to |
| `aes_key` | String | Base64-encoded AES-256 symmetric key |
| `risk_level` | Integer | Current escalation level (1–4), drives cumulative risk injection |
| `key_version` | Integer | Increments on every key rotation |
| `created_at` | DateTime | Session creation time |
| `updated_at` | DateTime | Last modification time |
| `is_active` | Boolean | `False` when session is deactivated (L4 containment or logout) |

#### `users` — Customer accounts

| Column | Type | Purpose |
|--------|------|---------|
| `id` | Integer PK | Auto-increment |
| `username` | String (unique, indexed) | Login identifier |
| `email` | String (unique, indexed) | For OTP delivery |
| `phone` | String (unique, indexed) | For SMS OTP delivery |
| `password_hash` | String | `salt:pbkdf2_hash` format |
| `email_verified` | Boolean | Must be True before login |
| `phone_verified` | Boolean | Must be True before login |
| `is_active` | Boolean | Account active status |
| `is_ghost` | Boolean | Non-loginable recipient account (see Ghost Recipients below) |
| `recovery_card_data` | JSON | `{A1: 7, B3: 2, ...}` for Tier 4 challenges |
| `created_at` | DateTime | Registration time |

#### `otp_verifications` — One-time password records

| Column | Type | Purpose |
|--------|------|---------|
| `id` | Integer PK | Auto-increment |
| `identifier` | String (indexed) | Email or phone number |
| `otp_hash` | String | PBKDF2-SHA256 hash of the 6-digit code (salt:hash format) |
| `channel` | String | `email` or `phone` |
| `purpose` | String | `registration` or `security_challenge` |
| `attempts` | Integer | Failed verification count (max 5) |
| `created_at` | DateTime | OTP generation time (expires after 10 minutes) |
| `is_used` | Boolean | Marked True after successful verification or expiry |

#### `aria_investigations` — ARIA autonomous investigation records

| Column | Type | Purpose |
|--------|------|---------|
| `id` | Integer PK | Auto-increment |
| `created_at` | DateTime | Investigation creation time |
| `updated_at` | DateTime | Last update time |
| `cluster_key` | String (indexed) | User ID being investigated |
| `cluster_event_ids` | JSON | List of SecurityEvent IDs in this cluster |
| `cycle` | Integer | Number of ARIA scan passes that touched this investigation |
| `hypothesis` | String | ARIA's threat hypothesis |
| `classification` | String | `social_engineering_chain`, `ato_fraud`, `coordinated_attack`, `elevated_cluster`, or `unknown` |
| `evidence_summary` | String | Grounded evidence from actual event data |
| `vlm_assessment` | String | Qwen VLM's natural-language analysis |
| `confidence` | Float | ARIA's confidence in the classification |
| `status` | String | `open`, `resolved`, or `fp_confirmed` (false positive) |

#### `beneficiaries` — Saved payment recipients

| Column | Type | Purpose |
|--------|------|---------|
| `id` | Integer PK | Auto-increment |
| `user_id` | String (indexed) | Owner of this beneficiary |
| `name` | String | Beneficiary display name |
| `account_number` | String | Bank account number |
| `bank_name` | String | Bank name |
| `is_ghost` | Boolean | Auto-created ghost recipient |
| `created_at` | DateTime | Creation time |

#### `revoked_tokens` — JWT blacklist

| Column | Type | Purpose |
|--------|------|---------|
| `id` | Integer PK | Auto-increment |
| `jti` | String (unique, indexed) | JWT token identifier |
| `revoked_at` | DateTime | Revocation timestamp |

### Schema Migrations (`_migrate_schema()`)

SQLite doesn't support adding columns via `CREATE TABLE IF NOT EXISTS`. The `_migrate_schema()` function handles forward-compatible schema evolution:

1. Read existing column names via `PRAGMA table_info(table)`
2. For each expected column not present, execute `ALTER TABLE ... ADD COLUMN`
3. Currently migrates:
   - `security_events`: `user_id`, `session_id`, `event_category`
   - `users`: `is_ghost`, `recovery_card_data`

---

## 5.2 Session Cryptography (`src/api/internal/session_crypto.py`)

### Design Constraint
The crypto implementation is **pure Python** (stdlib `hashlib`, `hmac`, `secrets`) — no compiled Rust DLLs. This was necessary because Windows AppLocker in the competition environment blocks compiled extensions from non-whitelisted publishers, which breaks the `cryptography` package's Rust backend.

### HMAC-SHA256-CTR AEAD Cipher

#### Key Generation
```python
def generate_aes_key() -> str:
    return base64.b64encode(secrets.token_bytes(32)).decode()  # 256-bit random key
```

#### Encryption (`encrypt_aes_gcm()`)
Despite the function name (legacy naming), this is HMAC-CTR with Encrypt-then-MAC:

1. Generate 16-byte random nonce
2. **Keystream generation** (CTR mode):
   ```
   for counter = 0, 1, 2, ...:
       block = HMAC-SHA256(key, nonce || counter_4bytes)
       keystream += block
   ```
3. **Encrypt**: `ciphertext = plaintext XOR keystream[:len(plaintext)]`
4. **Authenticate** (Encrypt-then-MAC): `tag = HMAC-SHA256(key, nonce || ciphertext)`
5. Return `{ciphertext, nonce, tag}` all base64-encoded

#### Decryption (`decrypt_aes_gcm()`)
1. Verify MAC first: `expected = HMAC-SHA256(key, nonce || ciphertext)`
2. Compare using `hmac.compare_digest()` (constant-time)
3. If tag doesn't match → raise "Cryptographic integrity check failed"
4. Regenerate keystream and XOR to recover plaintext

### Pure-Python JWT (HS256)

#### Encoding
```
header  = base64url({"alg":"HS256","typ":"JWT"})
payload = base64url({sub, surface, iat, exp, jti, ...})
signature = HMAC-SHA256(secret, header.payload)
token = header.payload.base64url(signature)
```

#### Decoding
1. Split token into 3 parts
2. Verify signature using `hmac.compare_digest()`
3. Check `exp` claim against current time
4. Return decoded payload

### JWT Secrets
Three per-surface secrets, loaded from environment variables:
```
CUSTOMER_JWT_SECRET  → "customer" surface
ADMIN_JWT_SECRET     → "admin" surface
ATTACKER_JWT_SECRET  → "attacker" surface
```
Default values are hardcoded but a warning is emitted if used without `ALLOW_DEFAULT_SECRETS=1`.

### Token Verification
`verify_jwt_token(token, surface, db)`:
1. Decode JWT with the surface-specific secret
2. Check `surface` claim matches expected surface (prevents cross-surface token reuse)
3. Check JTI against `revoked_tokens` table (blacklist)
4. Return payload

### Key Rotation (Escalation)
`shuffle_session_key(session, new_risk_level, db)`:
1. Generate new AES-256 key
2. Update session: `aes_key`, `key_version += 1`, `risk_level`
3. If L4: `is_active = False` (session deactivated)
4. Return new key and version to the API response

---

## 5.3 Password Security

### Hashing
PBKDF2-SHA256 with:
- Random 16-byte hex salt
- **260,000 iterations** (exceeds OWASP minimum of 210,000)
- Storage format: `salt:hex_hash`

### Verification
```python
def verify_password(password, stored):
    salt, h = stored.split(':', 1)
    expected = pbkdf2_hmac('sha256', password, salt, 260000)
    return hmac.compare_digest(expected.hex(), h)
```
Uses constant-time comparison to prevent timing attacks.

### OTP Hashing
Same PBKDF2 approach but with 100,000 iterations (lower because OTP space is only 10^6 values).

---

## 5.4 Recovery Card (`src/api/internal/recovery_card.py`)

### Purpose
Physical-card-based identity verification for Tier 4 (CONTAIN) recovery. Each customer gets a unique 6×6 grid card at enrollment.

### Card Generation
```python
def generate_card() -> Dict[str, int]:
    # {A1: 7, A2: 3, ..., F6: 1} — 36 random digits
    return {f"{c}{r}": secrets.randbelow(10) for c in "ABCDEF" for r in "123456"}
```

### Challenge Generation
```python
def make_challenge(n=2) -> List[str]:
    # Pick 2 random positions, e.g. ['B3', 'D5']
    return sorted(SystemRandom().sample(all_36_positions, k=n))
```

### Card Rendering
`render_card_png(card, username)`:
- **Primary**: Pillow (PIL) — generates a PNG image with:
  - Navy header band with "CENTRAL BANK OF INDIA" branding
  - 6×6 grid with alternating light/white cells
  - Large readable digits in each cell
  - Footer: "Keep this card safe. Do not share."
- **Fallback**: SVG string when Pillow is unavailable

---

## 5.5 Ghost Recipient System

When a transfer or beneficiary-add targets an unknown recipient name:
1. `_create_ghost_recipient()` creates a `User` record with `is_active=False`, `is_ghost=True`
2. Creates a `Beneficiary` row linked to the customer
3. The risk engine sees `is_new_beneficiary=True`, which triggers the 1.5× weight boost for `TransactionRiskProvider`

This makes "unknown recipient" a real risk signal without requiring pre-seeded recipient databases.

---

## 5.6 Four-Tier Security Escalation (Customer-Facing)

| Level | Decision | Customer Experience | Recovery Path |
|:---:|---|---|---|
| L1 | ALLOW | Normal banking | — |
| L2 | CHALLENGE | OTP required before sensitive actions | Enter email OTP via `POST /customer/auth/challenge-otp` |
| L3 | RESTRICT | Password reset required; sensitive ops locked | OTP + new password |
| L4 | CONTAIN | Session deactivated (`is_active=False`) | OTP + Recovery Card coordinates + new password |

**Key Rotation**: `shuffle_session_key()` rotates the AES-256 session key on every level increase.

**De-escalation**: `maybe_deescalate()` steps the risk level down by 1 if the current evaluation is clean (L1) and the session is elevated. This prevents abrupt drops while allowing gradual trust recovery.
