"""Phase 1 — backend contract, against the LIVE running stack (127.0.0.1:8001-8004).

Endpoints confirmed from source (NOT assumed):
  - customer 'profile'      -> POST /customer/account       (encrypted)
  - customer beneficiaries  -> POST /customer/beneficiaries (empty body = list)
  - customer transactions   -> POST /customer/statements     (encrypted list)
  - encrypted request shape -> {session_id,key_version,ciphertext,nonce,tag}
There is NO GET /customer/profile / GET /customer/beneficiaries — the plan's names
map to the encrypted POSTs above (recorded as a finding).
"""
import json
import httpx
import pytest

from src.api.internal.session_crypto import encrypt_aes_gcm, decrypt_aes_gcm

CUST = "http://127.0.0.1:8001"
ADMIN = "http://127.0.0.1:8002"
ATTK = "http://127.0.0.1:8003"
SEED_USER, SEED_PW = "keshav", "DemoPass@Mnit2026!"

CLIP_FLAGS = []   # collected exact-0.0/1.0 scores for manual review (non-failing)


def _enc(body: dict, sess: dict) -> dict:
    e = encrypt_aes_gcm(json.dumps(body), sess["aes_key"])
    return {"session_id": sess["session_id"], "key_version": sess["key_version"], **e}


def _dec(resp_json: dict, sess: dict):
    return json.loads(decrypt_aes_gcm(resp_json["ciphertext"], resp_json["nonce"], resp_json["tag"], sess["aes_key"]))


@pytest.fixture(scope="module")
def customer():
    r = httpx.post(f"{CUST}/customer/auth/login", json={"username": SEED_USER, "password": SEED_PW}, timeout=15)
    assert r.status_code == 200, f"customer login failed: {r.status_code} {r.text}"
    j = r.json()
    j["_token"] = j.get("token")
    return j


@pytest.fixture(scope="module")
def admin_cookie():
    r = httpx.post(f"{ADMIN}/admin/auth/login", json={"username": "admin", "password": "admin123"}, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return r.cookies


@pytest.fixture(scope="module")
def attacker_cookie():
    r = httpx.post(f"{ATTK}/attacker/auth/login", json={"username": "attacker", "password": "attack123"}, timeout=15)
    assert r.status_code == 200, f"attacker login failed: {r.status_code} {r.text}"
    return r.cookies


def _hdr(sess):
    return {"Authorization": f"Bearer {sess['_token']}"} if sess.get("_token") else {}


# ── 1. Auth ───────────────────────────────────────────────────────────────────
def test_customer_login_ok_and_wrong():
    ok = httpx.post(f"{CUST}/customer/auth/login", json={"username": SEED_USER, "password": SEED_PW}, timeout=15)
    assert ok.status_code == 200 and ok.json().get("session_id")
    bad = httpx.post(f"{CUST}/customer/auth/login", json={"username": SEED_USER, "password": "wrong"}, timeout=15)
    assert bad.status_code == 401


def test_admin_attacker_login(admin_cookie, attacker_cookie):
    assert admin_cookie and attacker_cookie
    bad = httpx.post(f"{ADMIN}/admin/auth/login", json={"username": "admin", "password": "nope"}, timeout=15)
    assert bad.status_code == 401


# ── 2. Encrypted round-trip ─────────────────────────────────────────────────────
def test_encrypted_roundtrip_and_tamper(customer):
    r = httpx.post(f"{CUST}/customer/account", json=_enc({}, customer), headers=_hdr(customer), timeout=15)
    assert r.status_code == 200, r.text
    acct = _dec(r.json(), customer)
    assert isinstance(acct, (dict, list)) and acct, "account payload empty"
    # tamper the tag → must be rejected
    bad = _enc({}, customer); bad["tag"] = bad["tag"][:-2] + ("AA" if not bad["tag"].endswith("AA") else "BB")
    rt = httpx.post(f"{CUST}/customer/account", json=bad, headers=_hdr(customer), timeout=15)
    assert rt.status_code in (400, 401), f"tampered tag not rejected: {rt.status_code}"


# ── 3. Customer CRUD + 7. empty-state ───────────────────────────────────────────
def test_beneficiaries_list_nonempty(customer):
    r = httpx.post(f"{CUST}/customer/beneficiaries", json=_enc({}, customer), headers=_hdr(customer), timeout=15)
    assert r.status_code == 200, r.text
    data = _dec(r.json(), customer)
    items = data if isinstance(data, list) else data.get("beneficiaries", data)
    assert isinstance(items, list) and len(items) >= 12, f"seeded DB returned {len(items)} beneficiaries (empty-state bug)"


def test_telemetry_ingest(customer):
    ev = {"session_id": customer["session_id"],
          "events": [{"type": "keystroke", "timestamp": 1735000000000 + i * 120,
                      "data": {"event": "dwell", "dwellTime": 90, "key": "A", "code": "KeyA"}} for i in range(5)]}
    r = httpx.post(f"{CUST}/customer/telemetry", json=ev, timeout=15)
    assert r.status_code == 200 and r.json().get("count") == 5, r.text


# ── 3/4. Transfer + ledger cross-check ──────────────────────────────────────────
def test_transfer_and_statement_ledger(customer):
    # get a real beneficiary id
    b = httpx.post(f"{CUST}/customer/beneficiaries", json=_enc({}, customer), headers=_hdr(customer), timeout=15)
    data = _dec(b.json(), customer)
    items = data if isinstance(data, list) else data.get("beneficiaries", data)
    bid = items[0]["id"]; payee = items[0]["name"]

    tr = httpx.post(f"{CUST}/customer/transfer",
                    json=_enc({"amount": 500, "beneficiary_id": bid, "is_new_beneficiary": False}, customer),
                    headers=_hdr(customer), timeout=20)
    assert tr.status_code == 200, tr.text
    res = _dec(tr.json(), customer)
    assert res.get("status") in ("approved", "challenged", "restricted", "blocked")

    # ledger cross-check via /customer/statements
    st = httpx.post(f"{CUST}/customer/statements", json=_enc({}, customer), headers=_hdr(customer), timeout=15)
    assert st.status_code == 200, st.text
    txns = _dec(st.json(), customer)
    txns = txns if isinstance(txns, list) else txns.get("transactions", [])
    if res.get("status") == "approved":
        hit = [t for t in txns if t.get("amount") == -500 and t.get("type") == "debit" and payee in str(t.get("description", ""))]
        assert hit, f"transfer not in statements ledger: {txns[:3]}"


# ── 5. Admin reads ──────────────────────────────────────────────────────────────
def test_admin_reads(admin_cookie):
    for path in ["/admin/sessions", "/admin/aria/investigations", "/admin/config"]:
        r = httpx.get(f"{ADMIN}{path}", cookies=admin_cookie, timeout=15)
        assert r.status_code == 200, f"{path}: {r.status_code} {r.text[:200]}"
        assert r.json() is not None


def test_admin_sessions_nonempty_and_live(admin_cookie, customer):
    r = httpx.get(f"{ADMIN}/admin/sessions", cookies=admin_cookie, timeout=15)
    sessions = r.json()
    assert isinstance(sessions, list) and len(sessions) > 0, "no sessions after customer login (empty-state bug)"
    sid = customer["session_id"]
    live = httpx.get(f"{ADMIN}/admin/sessions/{sid}/live", cookies=admin_cookie, timeout=15)
    assert live.status_code == 200, live.text
    assert "session" in live.json()


# ── 6. Attacker isolation ───────────────────────────────────────────────────────
def test_attacker_isolation(attacker_cookie):
    scen = httpx.get(f"{ATTK}/attacker/scenarios", cookies=attacker_cookie, timeout=15).json()
    assert scen, "no scenarios listed (empty-state bug)"
    name = next(iter(scen.keys()))
    run = httpx.post(f"{ATTK}/attacker/scenarios/{name}/run", cookies=attacker_cookie, timeout=60)
    assert run.status_code == 200, run.text
    j = run.json()
    assert j["session_id"].startswith("sim_") and j["user_id"].startswith("sim_"), "attacker wrote non-sim ids"
    assert "keshav" not in j["session_id"] and "keshav" not in j["user_id"]
    # 8. clip guard — scan provider scores in the run
    for step in j.get("steps", []):
        for pname, pdata in step.get("result", {}).get("provider_breakdown", {}).items():
            for field in ("risk_score", "confidence"):
                v = pdata.get(field)
                if v in (0.0, 1.0):
                    CLIP_FLAGS.append(f"{name}/{step['label']}: {pname}.{field}=={v}")


def test_clip_guard_report():
    # non-failing: surface exact 0.0/1.0 scores for manual review
    if CLIP_FLAGS:
        print("\n[CLIP-GUARD FLAGS for manual review]")
        for f in sorted(set(CLIP_FLAGS)):
            print("  ", f.encode("ascii", "replace").decode())
