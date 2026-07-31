"""X25519 conformance — RFC 7748 known-answer vector + DH commutativity.

Vector 1 is the authoritative RFC 7748 §5.2 test vector (known answer). The
Diffie-Hellman commutativity property is the gold-standard functional check:
any correct X25519 must satisfy X25519(a, X25519(b,G)) == X25519(b, X25519(a,G)).
Together these pin the implementation to the standard.
"""
import os
from src.api.internal.pqcrypto import _x25519, x25519_keygen

_BASE = (9).to_bytes(32, "little")


def test_rfc7748_vector1():
    scalar = bytes.fromhex("a546e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449ac4")
    u = bytes.fromhex("e6db6867583030db3594c1a424b15f7c726624ec26b3353b10a903a6d0ab1c4c")
    expected = "c3da55379de9c6908e94ea4df28d084f32eccf03491c71f754b4075577a28552"
    assert _x25519(scalar, u).hex() == expected


def test_dh_commutativity():
    # a and b are independent secrets; shared secret must match from both sides.
    a = os.urandom(32)
    b = os.urandom(32)
    pub_a = _x25519(a, _BASE)
    pub_b = _x25519(b, _BASE)
    assert _x25519(a, pub_b) == _x25519(b, pub_a)


def test_keygen_uses_basepoint():
    pk, sk = x25519_keygen()
    assert pk == _x25519(sk, _BASE)
    assert len(pk) == 32 and len(sk) == 32
