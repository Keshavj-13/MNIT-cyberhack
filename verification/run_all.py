"""Single entry point for the BEACON verification suite.

    python -m verification.run_all            # run everything, one pass/fail
    python -m verification.run_all -k mitm    # forward args to pytest

Exit code 0 iff every non-skipped check passes. External-toolchain checks
(ProVerif, TLC) skip cleanly when the tools aren't installed; everything else
runs on the plain Python environment. `ALLOW_DEFAULT_SECRETS` is set for you.
"""
import os
import sys

os.environ.setdefault("ALLOW_DEFAULT_SECRETS", "1")

LAYERS = [
    ("Crypto conformance (X25519 RFC + ML-KEM sizes/roundtrip/reject/lock)", "verification/kat"),
    ("Reasoning proofs (Z3/SMT - universal)",                                 "verification/smt"),
    ("Reasoning code==spec (exhaustive) + metamorphic props",                 "verification/props"),
    ("Escalation state machine (shadow model check) + formal runners",        "verification/formal"),
    ("EWC continual learning (statistical)",                                  "verification/ewc"),
    ("End-to-end pipeline + robustness fuzz",                                 "verification/e2e"),
]


def main():
    import pytest
    extra = sys.argv[1:]
    targets = [p for _, p in LAYERS]
    print("=" * 74)
    print("BEACON VERIFICATION SUITE")
    for label, path in LAYERS:
        print(f"  - {label}\n      {path}")
    print("=" * 74)
    code = pytest.main([*targets, "-q", "--no-header", *extra])
    print("\n" + ("ALL VERIFICATION LAYERS PASSED [OK]" if code == 0
                  else f"FAILURES (pytest exit {code}) [FAIL]"))
    return code


if __name__ == "__main__":
    sys.exit(main())
