"""ML-KEM-768 conformance.

TWO distinct claims, kept honestly separate:

1. SELF-CONSISTENCY + REGRESSION LOCK (runs, must pass): correctness of the KEM
   (Encaps∘Decaps agree), implicit rejection on tampered ciphertext, FIPS-203
   byte sizes, and a deterministic self-vector lock so any accidental change to
   the crypto is caught. This proves the implementation is internally sound.

2. FIPS 203 CONFORMANCE (skipped until vectors present): the NIST ACVP
   known-answer vectors. Our pure-Python ML-KEM currently uses a self-consistent
   NTT/byte index order that is NOT yet aligned to the FIPS 203 wire format, so
   this WILL fail until that alignment work is done. The test is wired and will
   activate the moment verification/kat/mlkem768_acvp.json is added — it does not
   silently pass. This is the known, documented gap.
"""
import os
import json
import hashlib
import pytest

from src.api.internal.pqcrypto import (
    mlkem_keygen, mlkem_encaps, mlkem_decaps, mlkem_keygen_det, mlkem_encaps_det,
)

_HERE = os.path.dirname(__file__)
EK_LEN, DK_LEN, CT_LEN, SS_LEN = 1184, 2400, 1088, 32   # ML-KEM-768


def test_byte_sizes_match_fips203():
    ek, dk = mlkem_keygen()
    K, ct = mlkem_encaps(ek)
    assert (len(ek), len(dk), len(ct), len(K)) == (EK_LEN, DK_LEN, CT_LEN, SS_LEN)


def test_encaps_decaps_roundtrip():
    ek, dk = mlkem_keygen()
    for _ in range(10):
        K, ct = mlkem_encaps(ek)
        assert mlkem_decaps(dk, ct) == K


def test_implicit_rejection_on_tamper():
    ek, dk = mlkem_keygen()
    K, ct = mlkem_encaps(ek)
    bad = bytearray(ct); bad[0] ^= 0xFF
    got = mlkem_decaps(dk, bytes(bad))
    assert got != K            # FO transform: tamper yields the rejection key, not K
    assert len(got) == SS_LEN  # ...but still a well-formed 32-byte secret (no oracle)


def test_deterministic_selfvector_lock():
    """Locks the implementation against accidental change. NOT FIPS conformance."""
    with open(os.path.join(_HERE, "mlkem768_selfvectors.json")) as f:
        v = json.load(f)
    d = bytes.fromhex(v["seed_d"]); z = bytes.fromhex(v["seed_z"]); m = bytes.fromhex(v["msg_m"])
    ek, dk = mlkem_keygen_det(d, z)
    K, ct = mlkem_encaps_det(ek, m)
    assert hashlib.sha256(ek).hexdigest() == v["ek_sha256"], "ek changed — crypto regression"
    assert hashlib.sha256(dk).hexdigest() == v["dk_sha256"], "dk changed — crypto regression"
    assert hashlib.sha256(ct).hexdigest() == v["ct_sha256"], "ct changed — crypto regression"
    assert K.hex() == v["shared_secret"], "shared secret changed — crypto regression"


# ── FIPS 203 conformance (the honest gap) ─────────────────────────────────────
_ACVP = os.path.join(_HERE, "mlkem768_acvp.json")


@pytest.mark.skipif(not os.path.exists(_ACVP),
                    reason="NIST ACVP ML-KEM-768 vectors not present. Add mlkem768_acvp.json "
                           "to activate. EXPECTED TO FAIL until the NTT/byte order is aligned "
                           "to FIPS 203 — this is the documented conformance gap, not a pass.")
def test_fips203_acvp_conformance():
    with open(_ACVP) as f:
        vectors = json.load(f)
    for tc in vectors["keyGen"]:
        ek, dk = mlkem_keygen_det(bytes.fromhex(tc["d"]), bytes.fromhex(tc["z"]))
        assert ek.hex() == tc["ek"] and dk.hex() == tc["dk"], f"KeyGen tc {tc.get('tcId')}"
    for tc in vectors["encapDecap"]:
        K, ct = mlkem_encaps_det(bytes.fromhex(tc["ek"]), bytes.fromhex(tc["m"]))
        assert ct.hex() == tc["c"] and K.hex() == tc["k"], f"Encaps tc {tc.get('tcId')}"
