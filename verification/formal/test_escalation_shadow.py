"""Python shadow of verification/tla/Escalation.tla.

TLC needs a Java toolchain, so this reimplements the SAME escalation state
machine and exhaustively BFS-checks the SAME invariants in pure Python — the
formal escalation properties are therefore verified in CI unconditionally, with
the .tla file as the canonical artifact for when TLC is available. If the two
ever diverge, that is itself a bug to fix.
"""
MAX_VERSION = 8


def scheme_of(level):
    return "XWING" if level >= 4 else "SHA512" if level == 3 else "SHA256"


def strength(s):
    return {"SHA256": 1, "SHA512": 2, "XWING": 3}[s]


def successors(st):
    level, kv, active, scheme = st
    out = []
    if kv >= MAX_VERSION:
        return out
    if active:
        for new in range(level + 1, 5):                       # Escalate (multi-level)
            out.append((new, kv + 1, new < 4, scheme_of(new)))
        if level > 1:                                          # Deescalate one level
            out.append((level - 1, kv + 1, True, scheme_of(level - 1)))
    if not active and level == 4:                              # Recover L4 -> L1
        out.append((1, kv + 1, True, "SHA256"))
    return out


def reachable_states():
    init = (1, 1, True, "SHA256")
    seen, frontier = {init}, [init]
    while frontier:
        st = frontier.pop()
        for nxt in successors(st):
            if nxt not in seen:
                seen.add(nxt); frontier.append(nxt)
    return seen


STATES = reachable_states()


def test_type_ok():
    for level, kv, active, scheme in STATES:
        assert level in range(1, 5)
        assert 1 <= kv <= MAX_VERSION
        assert isinstance(active, bool)
        assert scheme in {"SHA256", "SHA512", "XWING"}


def test_scheme_matches_tier():
    for level, _, _, scheme in STATES:
        assert scheme == scheme_of(level), f"stale scheme {scheme} at L{level}"


def test_pqc_only_at_l4():
    for level, _, _, scheme in STATES:
        assert (scheme == "XWING") == (level == 4)


def test_l4_contained():
    for level, _, active, _ in STATES:
        assert not (level == 4 and active), "L4 must deactivate the session"


def test_hardened_above_l3():
    for level, _, _, scheme in STATES:
        if level >= 3:
            assert strength(scheme) >= 2


def test_recovery_always_enabled_when_contained():
    # Liveness surrogate: every contained state has a Recover transition, so
    # containment is never a dead end (L1 stays reachable).
    for st in STATES:
        level, _, active, _ = st
        if not active:
            assert any(nxt[0] == 1 for nxt in successors(st)) or st[1] >= MAX_VERSION


def test_state_space_nontrivial():
    assert len(STATES) > 10   # guard against an accidentally empty/collapsed model
