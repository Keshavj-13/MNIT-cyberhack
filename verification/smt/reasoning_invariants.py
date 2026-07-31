"""Machine-checked proofs of the concept-bottleneck reasoning logic (Z3/SMT).

`build_reasoning` (src/explainability/concept_bottleneck.py) is a pure function
over a tiny input space, so we don't have to *sample* it — we can prove
properties for ALL inputs at once. We encode the exact classification logic as
SMT constraints and ask Z3 to find a counterexample to each property. If Z3
returns `unsat`, no counterexample exists → the property holds universally =
a proof, not a test.

The encoding here is kept byte-for-byte faithful to build_reasoning; the
exhaustive truth-table test (verification/props/test_truth_table.py) runs the
REAL function over the whole finite space to guarantee code == this model.
"""
from z3 import (Solver, Bool, Real, Int, If, And, Or, Not, Implies, sat, unsat)

# attack_type enum (severity order matches _SEVERITY in concept_bottleneck.py)
CLEAN, PHISHING, BEHAVIORAL, MITM, HIJACK = 0, 1, 2, 3, 4
# crypto_action enum
AES, SHA512, MLKEM = 0, 1, 2


def _model():
    """Return (solver-vars, attack_expr, crypto_expr) mirroring build_reasoning."""
    ip = Bool("ip_changed")
    mac = Bool("mac_changed")
    oem = Bool("mac_oem_mismatch")
    url = Real("url_phishing_score")     # 0..100
    beh = Real("behavioral")             # 0..1  (max of beacon/ato)
    tier = Int("tier")                   # engine escalation level, 1..4

    # candidate concepts
    mitm_c = And(ip, mac)
    hij_c = And(ip, oem)
    phish_c = url > 60
    beh_c = beh > 0.5

    # highest severity wins: hijack(5) > mitm(4) > behavioral(3) > phishing(2)
    attack = If(hij_c, HIJACK,
             If(mitm_c, MITM,
             If(beh_c, BEHAVIORAL,
             If(phish_c, PHISHING, CLEAN))))
    # tier<=1 (engine allowed the action) forces the headline class to clean
    attack = If(tier <= 1, CLEAN, attack)

    crypto = If(tier >= 4, MLKEM, If(tier == 3, SHA512, AES))

    domain = [url >= 0, url <= 100, beh >= 0, beh <= 1, tier >= 1, tier <= 4,
              # the fingerprint invariant the real system guarantees: an OUI
              # mismatch implies the MAC changed (OEM is a prefix of the MAC).
              Implies(oem, mac)]
    v = {"ip_changed": ip, "mac_changed": mac, "mac_oem_mismatch": oem,
         "url": url, "behavioral": beh, "tier": tier}
    return v, attack, crypto, domain


def _prove(name, negation_extra):
    """Property holds iff (domain ∧ ¬property) is unsat."""
    v, attack, crypto, domain = _model()
    s = Solver()
    s.add(domain)
    s.add(negation_extra(v, attack, crypto))
    res = s.check()
    ok = res == unsat
    cex = s.model() if res == sat else None
    return ok, cex


# ── The properties (each returns the NEGATION Z3 tries to satisfy) ────────────

PROPERTIES = {
    # crypto_action is a strict function of tier — never AES at a tier that must
    # upgrade, and PQC (ML-KEM) appears only at tier 4.
    "crypto_follows_tier__no_AES_at_L3plus":
        lambda v, a, c: And(v["tier"] >= 3, c == AES),
    "PQC_only_at_L4":
        lambda v, a, c: And(c == MLKEM, v["tier"] != 4),
    "L3_is_SHA512":
        lambda v, a, c: And(v["tier"] == 3, c != SHA512),

    # attack_type ↔ decision consistency
    "tier1_implies_clean":
        lambda v, a, c: And(v["tier"] <= 1, a != CLEAN),

    # detection-logic correctness (under tier>=2 so the clean-gate doesn't mask it)
    "ip_and_oem_implies_hijack":
        lambda v, a, c: And(v["tier"] >= 2, v["ip_changed"], v["mac_oem_mismatch"], a != HIJACK),
    "ip_and_mac_noOEM_implies_MITM":
        lambda v, a, c: And(v["tier"] >= 2, v["ip_changed"], v["mac_changed"],
                            Not(v["mac_oem_mismatch"]), a != MITM),

    # enum closure: attack_type is always one of the five defined classes
    "attack_type_in_enum":
        lambda v, a, c: Not(Or(a == CLEAN, a == PHISHING, a == BEHAVIORAL, a == MITM, a == HIJACK)),
    "crypto_action_in_enum":
        lambda v, a, c: Not(Or(c == AES, c == SHA512, c == MLKEM)),
}


def prove_all():
    results = {}
    for name, neg in PROPERTIES.items():
        ok, cex = _prove(name, neg)
        results[name] = (ok, cex)
    return results


if __name__ == "__main__":
    allok = True
    for name, (ok, cex) in prove_all().items():
        print(f"  [{'PROVED ' if ok else 'FAILED '}] {name}")
        if not ok:
            allok = False
            print(f"      counterexample: {cex}")
    print("\nALL PROPERTIES PROVED (unsat = no counterexample exists)" if allok else "\nSOME PROPERTIES FAILED")
