"""Runners for the external formal-methods toolchains.

These execute the real tools (ProVerif, TLC) when they are on PATH, and SKIP
with an install hint otherwise — so the suite stays green on a machine without
the toolchains while still running the proofs on one that has them. They never
silently pass: a tool that is present but reports a failed query fails the test.
"""
import os
import shutil
import subprocess
import pytest

_HERE = os.path.dirname(__file__)
_PV_DIR = os.path.join(_HERE, "..", "proverif")
_TLA_DIR = os.path.join(_HERE, "..", "tla")


def _find_proverif():
    # PATH, explicit env var, then the stable local install used by this project.
    cand = (shutil.which("proverif") or shutil.which("proverif.exe")
            or os.environ.get("PROVERIF"))
    if cand and os.path.exists(cand):
        return cand
    for base in (os.path.expanduser("~/.local/proverif2.05"),
                 os.path.expanduser("~/.proverif")):
        for name in ("proverif", "proverif.exe"):
            p = os.path.join(base, name)
            if os.path.exists(p):
                return p
    return None


PROVERIF = _find_proverif()
TLC = shutil.which("tlc") or shutil.which("tlc2") or os.environ.get("TLC_JAR")


@pytest.mark.skipif(PROVERIF is None,
                    reason="proverif not on PATH. Install (opam install proverif) to run the "
                           "symbolic crypto proofs. Models: verification/proverif/*.pv")
@pytest.mark.parametrize("model", ["xwing_handshake.pv",
                                   "xwing_hybrid_classical_broken.pv",
                                   "xwing_hybrid_pq_broken.pv"])
def test_proverif_queries_hold(model):
    path = os.path.join(_PV_DIR, model)
    out = subprocess.run([PROVERIF, path], capture_output=True, text=True, timeout=300)
    # ProVerif prints "RESULT ... is true" per query; any "is false" = broken property.
    assert "is false" not in out.stdout, f"ProVerif refuted a query in {model}:\n{out.stdout[-2000:]}"
    assert "RESULT" in out.stdout, f"ProVerif produced no results for {model}:\n{out.stdout[-2000:]}"


@pytest.mark.skipif(TLC is None,
                    reason="TLC not on PATH. Install the TLA+ tools (tla2tools.jar) to model-check "
                           "the escalation machine. Spec: verification/tla/Escalation.tla. "
                           "(The same invariants are checked in Python by test_escalation_shadow.py.)")
def test_tlc_invariants_hold():
    cfg = os.path.join(_TLA_DIR, "Escalation.cfg")
    spec = os.path.join(_TLA_DIR, "Escalation.tla")
    cmd = ([TLC, "-config", cfg, spec] if not TLC.endswith(".jar")
           else ["java", "-jar", TLC, "-config", cfg, spec])
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=600, cwd=_TLA_DIR)
    assert "Error" not in out.stdout and "Invariant" not in out.stdout.split("violated")[0][-0:], out.stdout[-2000:]
    assert "No error has been found" in out.stdout or "0 errors" in out.stdout.lower(), \
        f"TLC reported a violation:\n{out.stdout[-2000:]}"
