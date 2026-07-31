---------------------------- MODULE Escalation ----------------------------
(*
  Tier escalation state machine for a customer session (L1..L4), model-checked
  with TLC. Mirrors customer_api.shuffle_session_key / maybe_deescalate and the
  crypto ladder in _key_for_tier.

  TLC explores EVERY reachable state, so a passing invariant is a proof over the
  whole state space, not a sample.

  Run:  tlc Escalation.tla -config Escalation.cfg
*)
EXTENDS Naturals

CONSTANTS MaxVersion            \* bound key_version so the state space is finite

VARIABLES level,                \* current risk tier 1..4
          keyVersion,           \* rotates on every escalation
          isActive,             \* session active flag
          scheme                \* "SHA256" | "SHA512" | "XWING"

vars == <<level, keyVersion, isActive, scheme>>

SchemeOf(l) == IF l >= 4 THEN "XWING" ELSE IF l = 3 THEN "SHA512" ELSE "SHA256"
Strength(s) == CASE s = "SHA256" -> 1 [] s = "SHA512" -> 2 [] s = "XWING" -> 3

Init ==
    /\ level = 1
    /\ keyVersion = 1
    /\ isActive = TRUE
    /\ scheme = "SHA256"

\* Escalate to any strictly-higher tier (multi-level jumps allowed, e.g. L1->L4).
Escalate ==
    /\ isActive = TRUE
    /\ keyVersion < MaxVersion
    /\ \E new \in (level+1)..4 :
        /\ level' = new
        /\ keyVersion' = keyVersion + 1          \* key ALWAYS rotates on escalation
        /\ scheme' = SchemeOf(new)
        /\ isActive' = (new < 4)                 \* L4 contains the session

\* De-escalate one level on a clean event (never below 1); also rotates key.
Deescalate ==
    /\ isActive = TRUE
    /\ level > 1
    /\ keyVersion < MaxVersion
    /\ level' = level - 1
    /\ keyVersion' = keyVersion + 1
    /\ scheme' = SchemeOf(level - 1)
    /\ isActive' = TRUE

\* Recovery from containment: L4 -> L1 after OTP + recovery-card + new key.
Recover ==
    /\ isActive = FALSE
    /\ level = 4
    /\ keyVersion < MaxVersion
    /\ level' = 1
    /\ keyVersion' = keyVersion + 1
    /\ scheme' = "SHA256"
    /\ isActive' = TRUE

Next == Escalate \/ Deescalate \/ Recover
Spec == Init /\ [][Next]_vars /\ WF_vars(Recover)

------------------------------------------------------------------------------
\* INVARIANTS (must hold in every reachable state)

TypeOK ==
    /\ level \in 1..4
    /\ keyVersion \in 1..MaxVersion
    /\ isActive \in BOOLEAN
    /\ scheme \in {"SHA256", "SHA512", "XWING"}

\* Crypto scheme is a strict function of the tier (no stale scheme after a move).
SchemeMatchesTier == scheme = SchemeOf(level)

\* Post-quantum key material appears ONLY at the containment tier.
PQCOnlyAtL4 == (scheme = "XWING") <=> (level = 4)

\* L4 always deactivates the session.
L4Contained == (level = 4) => (isActive = FALSE)

\* Any tier at or above 3 must be on a hardened (>=SHA512) scheme.
HardenedAboveL3 == (level >= 3) => (Strength(scheme) >= 2)

------------------------------------------------------------------------------
\* LIVENESS: containment is never a dead end — L1 is always reachable again.
RecoveryPossible == (isActive = FALSE) ~> (level = 1)

=============================================================================
