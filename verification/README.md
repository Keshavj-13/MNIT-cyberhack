# BEACON Verification Suite

Automated verification for the five BEACON modules. Each proof obligation is
matched to the right tool: symbolic protocol proofs, standards conformance,
exhaustive model checking, SMT, and statistical validation. The whole thing is
one command.

```bash
pip install -r verification/requirements-verify.txt
python -m verification.run_all
```

Exit code `0` iff every non-skipped check passes. Runs on the plain Python
environment; the two external formal toolchains (ProVerif, TLA+/TLC) **skip
cleanly** when not installed and run the proofs when they are.

## What each layer proves — and how strong the guarantee is

| Layer | Dir | Tool | Guarantee | Runs today |
|---|---|---|---|---|
| Crypto conformance | `kat/` | pytest | X25519 = RFC 7748 vector + DH commutativity; ML-KEM-768 FIPS sizes, encaps/decaps round-trip, implicit rejection, deterministic regression lock | ✅ |
| Reasoning invariants | `smt/` | **Z3/SMT** | **Proof** (∀ inputs, `unsat` = no counterexample): crypto follows tier, PQC only at L4, tier≤1⇒clean, hijack precedence, enum closure | ✅ |
| Reasoning code=spec | `props/` | pytest + Hypothesis | Exhaustive truth-table: real `build_reasoning` == independent spec over the whole finite input space; metamorphic monotonicity properties | ✅ |
| Escalation machine | `formal/` + `tla/` | Python BFS + **TLA+/TLC** | Exhaustive state-space check: key always rotates, L4⇒contained, scheme matches tier, hardened ≥L3, recovery reachable | ✅ (TLC optional) |
| EWC continual learning | `ewc/` | pytest + numpy | **Statistical**: 20-seed mean±95% CI, EWC forgets significantly less than naive, plasticity retained, Fisher = finite-difference gradient | ✅ |
| End-to-end + fuzz | `e2e/` | pytest + Hypothesis | Real pipeline: MITM⇒L4+X-Wing, hijack classified, reasoning persisted, fingerprint enrolls-before-flagging; 500 fuzzed payloads never crash / scores bounded | ✅ |
| Crypto protocol | `proverif/` | **ProVerif 2.05** | Symbolic (Dolev-Yao): session-key secrecy, injective agreement, **hybrid resilience** BOTH directions (leak either KEM's secret ⇒ key still secret) | ✅ installed, 4/4 queries `true` |
| Crypto computational | `cryptoverif/` | CryptoVerif | Computational IND-CCA — **cited** (published X-Wing proof), template to reproduce | pointer |

## The honest caveats (read these)

1. **ML-KEM is not yet FIPS-203-conformant.** The pure-Python ML-KEM-768 is
   internally correct (round-trips, rejects tampering, right sizes) and
   regression-locked, but its NTT/byte index order is self-consistent rather
   than aligned to the FIPS 203 wire format. The NIST ACVP known-answer test in
   `kat/test_mlkem_kat.py` is wired and **will fail** the moment you drop in
   `mlkem768_acvp.json` — it does not silently pass. Closing this gap = aligning
   `ByteEncode`/NTT ordering to the spec. "Verified PQC" needs ProVerif (design)
   **and** KAT (bytes); we're honest about having the first and a self-lock, not
   the second, for ML-KEM.

2. **ProVerif proves the protocol, not the Python** (and it now runs — 4/4
   queries `true`). It treats the KEM as a perfect primitive: it certifies the
   handshake *design* is sound against an active attacker (secrecy, auth, hybrid
   resilience), not that the implementation bytes are bug-free — that's what KAT
   is for. This is exactly why the two layers are paired.

3. **EWC is validated, not proved.** Learning behaviour can't be a theorem;
   `ewc/` gives confidence intervals and a significance test with pinned seeds
   (deterministic pass/fail), asserting "EWC forgets significantly less," not a
   universal guarantee.

4. **TLA+ and the Python shadow check the same invariants.** `formal/
   test_escalation_shadow.py` BFS-checks the escalation properties in pure Python
   so they're verified in CI unconditionally; `tla/Escalation.tla` is the
   canonical formal artifact for when TLC is installed. If they diverge, that's a
   bug.

## External formal tools

- **ProVerif 2.05 — installed and passing.** The official Inria Windows binary is
  installed at `~/.local/proverif2.05/proverif.exe`; the test runner discovers it
  there (or via `PROVERIF=/path/to/proverif`, or on `PATH`). All four queries
  across the three models return `true`:
  - `xwing_handshake.pv` — session-key secrecy + injective server→client authentication.
  - `xwing_hybrid_classical_broken.pv` — leak the **X25519** secret, key still secret (ML-KEM protects).
  - `xwing_hybrid_pq_broken.pv` — leak the **ML-KEM** secret, key still secret (X25519 protects).

  Run directly: `~/.local/proverif2.05/proverif.exe verification/proverif/xwing_handshake.pv`
- **TLA+/TLC — optional (needs a Java runtime, absent on this box).** The same
  escalation invariants are already exhaustively model-checked in Python by
  `formal/test_escalation_shadow.py`. To run the canonical TLC check, install a
  JRE, download `tla2tools.jar`, set `TLC_JAR=/path/tla2tools.jar`, then
  `python -m verification.run_all` picks it up (or:
  `java -jar tla2tools.jar -config Escalation.cfg Escalation.tla`).

## Layout

```
verification/
  run_all.py            single entry, one pass/fail
  kat/                  X25519 RFC + ML-KEM conformance/lock  (+ NIST ACVP slot)
  smt/                  Z3 universal proofs of the reasoning logic
  props/                exhaustive truth-table + Hypothesis metamorphic props
  formal/               Python escalation shadow-check + ProVerif/TLC runners
  proverif/             *.pv symbolic crypto models (secrecy, auth, hybrid)
  tla/                  Escalation.tla + .cfg  (escalation state machine)
  cryptoverif/          computational-proof pointer/template
  ewc/                  statistical validation of continual learning
  e2e/                  full-pipeline scenario replay + robustness fuzz
```
