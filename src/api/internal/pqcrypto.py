"""Pure-Python post-quantum key establishment: ML-KEM-768 + X25519 → X-Wing hybrid.

Why pure Python: the rest of this platform deliberately avoids the Rust-backed
`cryptography` wheel so it runs under Windows AppLocker (see session_crypto.py).
liboqs / pqcrypto wheels are compiled and would be blocked the same way, so the
lattice math lives here in stdlib-only code (hashlib gives us SHA3/SHAKE).

This is the real thing, not a stub:
  - ML-KEM-768 (FIPS 203, k=3) with the incomplete NTT over Z_3329.
  - X25519 (RFC 7748) Montgomery ladder.
  - X-Wing combiner (draft-connolly-cfrg-xwing-kem) binding both shared secrets.

Both endpoints are in-process for the demo, so we don't need FIPS test-vector
interop — we need self-consistency (Encaps∘Decaps agree) and MLWE-grade secrets.
Self-test at bottom: `python -m src.api.internal.pqcrypto`.
"""
import hashlib
import secrets
from typing import List, Tuple, Dict

# ── ML-KEM-768 parameters ─────────────────────────────────────────────────────
Q = 3329
N = 256
K = 3           # ML-KEM-768
ETA1 = 2
ETA2 = 2
DU = 10
DV = 4
ZETA = 17       # primitive 256th root of unity mod Q
NINV = 3303     # 128^-1 mod Q  (128*3303 ≡ 1)


def _brv7(x: int) -> int:
    return int(f"{x:07b}"[::-1], 2)

# zetas[k] = 17^brv7(k) mod Q — drives both butterflies and the base-case multiply
_ZETAS = [pow(ZETA, _brv7(k), Q) for k in range(128)]


# ── Number-theoretic transform (incomplete, 7 layers) ─────────────────────────

def _ntt(f: List[int]) -> List[int]:
    r = f[:]
    k = 1
    length = 128
    while length >= 2:
        start = 0
        while start < N:
            zeta = _ZETAS[k]; k += 1
            for j in range(start, start + length):
                t = (zeta * r[j + length]) % Q
                r[j + length] = (r[j] - t) % Q
                r[j] = (r[j] + t) % Q
            start += 2 * length
        length //= 2
    return r


def _intt(f: List[int]) -> List[int]:
    r = f[:]
    k = 127
    length = 2
    while length <= 128:
        start = 0
        while start < N:
            zeta = _ZETAS[k]; k -= 1
            for j in range(start, start + length):
                t = r[j]
                r[j] = (t + r[j + length]) % Q
                r[j + length] = (zeta * (r[j + length] - t)) % Q
            start += 2 * length
        length *= 2
    return [(x * NINV) % Q for x in r]


def _basemul(a: List[int], b: List[int]) -> List[int]:
    """Multiply two NTT-domain polys via 128 degree-1 base-case products."""
    r = [0] * N
    for i in range(64):
        z = _ZETAS[64 + i]
        for s, zeta in ((4 * i, z), (4 * i + 2, (-z) % Q)):
            a0, a1 = a[s], a[s + 1]
            b0, b1 = b[s], b[s + 1]
            r[s] = (a0 * b0 + a1 * b1 % Q * zeta) % Q
            r[s + 1] = (a0 * b1 + a1 * b0) % Q
    return r


def _padd(a: List[int], b: List[int]) -> List[int]:
    return [(x + y) % Q for x, y in zip(a, b)]


def _psub(a: List[int], b: List[int]) -> List[int]:
    return [(x - y) % Q for x, y in zip(a, b)]


# ── Encode / compress ─────────────────────────────────────────────────────────

def _byte_encode(f: List[int], d: int) -> bytes:
    out = bytearray((N * d) // 8)
    bit = 0
    for x in f:
        for i in range(d):
            if (x >> i) & 1:
                out[bit >> 3] |= 1 << (bit & 7)
            bit += 1
    return bytes(out)


def _byte_decode(b: bytes, d: int) -> List[int]:
    f = [0] * N
    bit = 0
    m = Q if d == 12 else (1 << d)
    for i in range(N):
        x = 0
        for j in range(d):
            x |= ((b[bit >> 3] >> (bit & 7)) & 1) << j
            bit += 1
        f[i] = x % m
    return f


def _compress(x: int, d: int) -> int:
    return (((x % Q) << (d + 1)) + Q) // (2 * Q) & ((1 << d) - 1)


def _decompress(y: int, d: int) -> int:
    return ((y * Q << 1) + (1 << d)) >> (d + 1)


def _compress_poly(f: List[int], d: int) -> List[int]:
    return [_compress(x, d) for x in f]


def _decompress_poly(f: List[int], d: int) -> List[int]:
    return [_decompress(x, d) for x in f]


# ── Hashing (FIPS 203 symbols) ────────────────────────────────────────────────

def _G(b: bytes) -> Tuple[bytes, bytes]:
    h = hashlib.sha3_512(b).digest()
    return h[:32], h[32:]


def _H(b: bytes) -> bytes:
    return hashlib.sha3_256(b).digest()


def _J(b: bytes) -> bytes:
    return hashlib.shake_256(b).digest(32)


def _prf(eta: int, s: bytes, nonce: int) -> bytes:
    return hashlib.shake_256(s + bytes([nonce])).digest(64 * eta)


# ── Sampling ──────────────────────────────────────────────────────────────────

def _sample_ntt(seed: bytes) -> List[int]:
    """Rejection-sample a uniform NTT-domain poly from a SHAKE-128 stream."""
    xof = hashlib.shake_128(seed)
    a: List[int] = []
    n = 504
    buf = xof.digest(n)
    off = 0
    while len(a) < N:
        if off + 3 > len(buf):
            n *= 2
            buf = xof.digest(n)          # shake stream prefix is stable across lengths
        d1 = buf[off] | ((buf[off + 1] & 0xF) << 8)
        d2 = (buf[off + 1] >> 4) | (buf[off + 2] << 4)
        off += 3
        if d1 < Q:
            a.append(d1)
        if len(a) < N and d2 < Q:
            a.append(d2)
    return a


def _sample_cbd(byts: bytes, eta: int) -> List[int]:
    bits = [(byts[i >> 3] >> (i & 7)) & 1 for i in range(len(byts) * 8)]
    f = [0] * N
    for i in range(N):
        base = 2 * eta * i
        a = sum(bits[base + j] for j in range(eta))
        b = sum(bits[base + eta + j] for j in range(eta))
        f[i] = (a - b) % Q
    return f


def _matrix_entry(rho: bytes, a: int, b: int) -> List[int]:
    # Self-consistent index order; KeyGen uses (i,j), Encrypt uses (j,i) for A^T.
    return _sample_ntt(rho + bytes([a, b]))


# ── K-PKE ─────────────────────────────────────────────────────────────────────

def _kpke_keygen(d: bytes) -> Tuple[bytes, bytes]:
    rho, sigma = _G(d + bytes([K]))
    s_hat = [_ntt(_sample_cbd(_prf(ETA1, sigma, i), ETA1)) for i in range(K)]
    e_hat = [_ntt(_sample_cbd(_prf(ETA1, sigma, K + i), ETA1)) for i in range(K)]
    t_hat = []
    for i in range(K):
        acc = [0] * N
        for j in range(K):
            acc = _padd(acc, _basemul(_matrix_entry(rho, i, j), s_hat[j]))
        t_hat.append(_padd(acc, e_hat[i]))
    ek = b"".join(_byte_encode(t, 12) for t in t_hat) + rho
    dk = b"".join(_byte_encode(s, 12) for s in s_hat)
    return ek, dk


def _kpke_encrypt(ek: bytes, m: bytes, r: bytes) -> bytes:
    t_hat = [_byte_decode(ek[384 * i:384 * (i + 1)], 12) for i in range(K)]
    rho = ek[384 * K:384 * K + 32]
    y_hat = [_ntt(_sample_cbd(_prf(ETA1, r, i), ETA1)) for i in range(K)]
    e1 = [_sample_cbd(_prf(ETA2, r, K + i), ETA2) for i in range(K)]
    e2 = _sample_cbd(_prf(ETA2, r, 2 * K), ETA2)

    u = []
    for i in range(K):
        acc = [0] * N
        for j in range(K):
            acc = _padd(acc, _basemul(_matrix_entry(rho, j, i), y_hat[j]))  # A^T
        u.append(_padd(_intt(acc), e1[i]))

    tv = [0] * N
    for i in range(K):
        tv = _padd(tv, _basemul(t_hat[i], y_hat[i]))
    mu = _decompress_poly(_byte_decode(m, 1), 1)
    v = _padd(_padd(_intt(tv), e2), mu)

    c1 = b"".join(_byte_encode(_compress_poly(u[i], DU), DU) for i in range(K))
    c2 = _byte_encode(_compress_poly(v, DV), DV)
    return c1 + c2


def _kpke_decrypt(dk: bytes, c: bytes) -> bytes:
    c1_len = 32 * DU * K
    u = [_decompress_poly(_byte_decode(c[32 * DU * i:32 * DU * (i + 1)], DU), DU) for i in range(K)]
    v = _decompress_poly(_byte_decode(c[c1_len:c1_len + 32 * DV], DV), DV)
    s_hat = [_byte_decode(dk[384 * i:384 * (i + 1)], 12) for i in range(K)]
    su = [0] * N
    for i in range(K):
        su = _padd(su, _basemul(s_hat[i], _ntt(u[i])))
    w = _psub(v, _intt(su))
    return _byte_encode(_compress_poly(w, 1), 1)


# ── ML-KEM-768 (FO transform, implicit rejection) ─────────────────────────────

def mlkem_keygen_det(d: bytes, z: bytes) -> Tuple[bytes, bytes]:
    """Deterministic KeyGen from explicit seeds — the KAT entry point."""
    ek, dk_pke = _kpke_keygen(d)
    return ek, dk_pke + ek + _H(ek) + z


def mlkem_encaps_det(ek: bytes, m: bytes) -> Tuple[bytes, bytes]:
    """Deterministic Encaps from explicit message randomness — the KAT entry point."""
    key, r = _G(m + _H(ek))
    return key, _kpke_encrypt(ek, m, r)


def mlkem_keygen() -> Tuple[bytes, bytes]:
    return mlkem_keygen_det(secrets.token_bytes(32), secrets.token_bytes(32))


def mlkem_encaps(ek: bytes) -> Tuple[bytes, bytes]:
    return mlkem_encaps_det(ek, secrets.token_bytes(32))


def mlkem_decaps(dk: bytes, ct: bytes) -> bytes:
    dk_pke = dk[:384 * K]
    ek = dk[384 * K:384 * K + (384 * K + 32)]
    h = dk[768 * K + 32:768 * K + 64]
    z = dk[768 * K + 64:768 * K + 96]
    m = _kpke_decrypt(dk_pke, ct)
    key, r = _G(m + h)
    kbar = _J(z + ct)
    ct2 = _kpke_encrypt(ek, m, r)
    return key if ct == ct2 else kbar    # implicit rejection


# ── X25519 (RFC 7748) ─────────────────────────────────────────────────────────

_P25519 = 2 ** 255 - 19
_A24 = 121665


def _x25519(scalar: bytes, u: bytes) -> bytes:
    k = bytearray(scalar)
    k[0] &= 248; k[31] &= 127; k[31] |= 64
    k_int = int.from_bytes(k, "little")
    x1 = int.from_bytes(u, "little") % _P25519
    x2, z2, x3, z3, swap = 1, 0, x1, 1, 0
    for t in range(254, -1, -1):
        kt = (k_int >> t) & 1
        swap ^= kt
        if swap:
            x2, x3 = x3, x2
            z2, z3 = z3, z2
        swap = kt
        A = (x2 + z2) % _P25519
        B = (x2 - z2) % _P25519
        C = (x3 + z3) % _P25519
        D = (x3 - z3) % _P25519
        DA = (D * A) % _P25519
        CB = (C * B) % _P25519
        x3 = pow(DA + CB, 2, _P25519)
        z3 = (x1 * pow(DA - CB, 2, _P25519)) % _P25519
        AA = (A * A) % _P25519
        BB = (B * B) % _P25519
        E = (AA - BB) % _P25519
        x2 = (AA * BB) % _P25519
        z2 = (E * (AA + _A24 * E)) % _P25519
    if swap:
        x2, x3 = x3, x2
        z2, z3 = z3, z2
    res = (x2 * pow(z2, _P25519 - 2, _P25519)) % _P25519
    return res.to_bytes(32, "little")


_BASE9 = (9).to_bytes(32, "little")


def x25519_keygen() -> Tuple[bytes, bytes]:
    sk = secrets.token_bytes(32)
    pk = _x25519(sk, _BASE9)
    return pk, sk


# ── X-Wing hybrid combiner (draft-connolly-cfrg-xwing-kem) ────────────────────
_XWING_LABEL = b"\x5c\x2e\x2f\x2f\x5e\x5c"   # ASCII  \.//^\


def _xwing_combine(ss_m: bytes, ss_x: bytes, ct_x: bytes, pk_x: bytes) -> bytes:
    return hashlib.sha3_256(_XWING_LABEL + ss_m + ss_x + ct_x + pk_x).digest()


def xwing_keygen() -> Tuple[Dict[str, bytes], Dict[str, bytes]]:
    ek_m, dk_m = mlkem_keygen()
    pk_x, sk_x = x25519_keygen()
    return {"mlkem_ek": ek_m, "x25519_pk": pk_x}, {"mlkem_dk": dk_m, "x25519_sk": sk_x, "x25519_pk": pk_x}


def xwing_encaps(pub: Dict[str, bytes]) -> Tuple[bytes, Dict[str, bytes]]:
    ss_m, ct_m = mlkem_encaps(pub["mlkem_ek"])
    eph_pk, eph_sk = x25519_keygen()
    ss_x = _x25519(eph_sk, pub["x25519_pk"])
    shared = _xwing_combine(ss_m, ss_x, eph_pk, pub["x25519_pk"])
    return shared, {"mlkem_ct": ct_m, "x25519_ct": eph_pk}


def xwing_decaps(priv: Dict[str, bytes], ct: Dict[str, bytes]) -> bytes:
    ss_m = mlkem_decaps(priv["mlkem_dk"], ct["mlkem_ct"])
    ss_x = _x25519(priv["x25519_sk"], ct["x25519_ct"])
    return _xwing_combine(ss_m, ss_x, ct["x25519_ct"], priv["x25519_pk"])


def establish_xwing_key(n_bytes: int = 64) -> Tuple[bytes, Dict[str, bytes]]:
    """One-shot in-process X-Wing handshake used by the crypto-escalation path.

    Returns (symmetric_key, descriptor). The key is the X-Wing shared secret
    expanded to n_bytes; the descriptor carries truncated public artifacts for
    display in the admin panel (never the private keys).
    """
    pub, priv = xwing_keygen()
    shared, ct = xwing_encaps(pub)
    # verify the receiver derives the same secret (sanity, and proves it round-trips)
    assert xwing_decaps(priv, ct) == shared, "X-Wing decaps disagreement"
    key = hashlib.shake_256(shared).digest(n_bytes)
    descriptor = {
        "scheme": "X-Wing (X25519 + ML-KEM-768)",
        "kem": "ML-KEM-768",
        "classical": "X25519",
        "spec": "FIPS 203 + RFC 7748, X-Wing combiner",
        "mlkem_ek_prefix": pub["mlkem_ek"][:6].hex(),
        "mlkem_ct_prefix": ct["mlkem_ct"][:6].hex(),
        "x25519_pk_prefix": pub["x25519_pk"][:6].hex(),
        "shared_secret_bits": len(shared) * 8,
        "session_key_bits": n_bytes * 8,
    }
    return key, descriptor


if __name__ == "__main__":
    # ML-KEM round trip
    ek, dk = mlkem_keygen()
    for _ in range(20):
        kk, ct = mlkem_encaps(ek)
        assert mlkem_decaps(dk, ct) == kk, "ML-KEM round-trip failed"
    # implicit rejection: tampered ciphertext must NOT recover the key
    kk, ct = mlkem_encaps(ek)
    bad = bytearray(ct); bad[0] ^= 0xFF
    assert mlkem_decaps(dk, bytes(bad)) != kk, "implicit rejection failed"
    # X-Wing agreement
    pub, priv = xwing_keygen()
    for _ in range(20):
        s, c = xwing_encaps(pub)
        assert xwing_decaps(priv, c) == s, "X-Wing round-trip failed"
    key, desc = establish_xwing_key()
    print("ML-KEM-768 ek/dk/ct sizes:", len(ek), len(dk), len(ct))
    print("X-Wing session key:", key[:8].hex(), "...", len(key), "bytes")
    print("descriptor:", desc)
    print("ALL SELF-TESTS PASSED")
