"""Concept Bottleneck layer — turns provider scores into a human-readable decision.

A black-box model maps signals X → decision Y and you cannot ask it *why*. A
concept bottleneck instead forces X → concepts C → Y, where C is a short list of
human-named intermediate concepts (ip_changed, url_phishing, behavioral_drift…).
The final class is a function of the concepts alone, so the explanation isn't a
post-hoc guess (SHAP/LIME) — it *is* the computation path.

Here the provider ensemble already produces the concept activations (each
provider IS a concept detector). This module reads those activations plus the
injected fingerprint flags, classifies the attack, and emits the structured
reasoning contract the SOC console and ARIA consume.
"""
from typing import Dict, Any, List

# Attack severity ordering — used when several concepts fire at once
# ("combinations → highest severity"). Higher wins. session_hijack outranks
# MITM: a MAC OEM (vendor block) mismatch is the *specific* device-spoofing
# tell, so it should win over the generic "both changed" MITM signal that it
# necessarily also trips.
_SEVERITY = {"clean": 0, "phishing": 2, "behavioral_anomaly": 3,
             "MITM": 4, "session_hijack": 5}


def _provider(breakdown: Dict[str, Any], name: str) -> Dict[str, Any]:
    """Fetch a provider result by RiskResult.provider_name (dict or model)."""
    for res in (breakdown or {}).values():
        r = res if isinstance(res, dict) else res.dict()
        if r.get("provider_name") == name:
            return r
    return {}


def build_reasoning(result, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Produce the JSON reasoning-layer output from an EngineResult + payload.

    result: EngineResult (has provider_breakdown, escalation_level, confidence).
    payload: the enriched payload actually evaluated (carries fingerprint flags).
    """
    breakdown = result.provider_breakdown
    tier = result.escalation_level

    # ── Read concept activations ──────────────────────────────────────────────
    url_score = round(_provider(breakdown, "URLPhishing").get("risk_score", 0.0) * 100, 1)
    fp = _provider(breakdown, "SessionFingerprint")
    ip_changed = bool(payload.get("ip_changed"))
    mac_changed = bool(payload.get("mac_changed"))
    oem_mismatch = bool(payload.get("mac_oem_mismatch"))
    beacon_score = _provider(breakdown, "BeaconBehavioral (Ensemble)").get("risk_score", 0.0)
    ato_score = _provider(breakdown, "AccountTakeover").get("risk_score", 0.0)
    txn_score = _provider(breakdown, "TransactionRisk").get("risk_score", 0.0)
    net = _provider(breakdown, "NetworkRisk")
    behavioral = max(beacon_score, ato_score)

    # ── Build the triggered-concept list (the bottleneck) ─────────────────────
    concepts: List[str] = []
    if url_score > 60:
        concepts.append(f"url_phishing_score: {url_score:.0f} → page URL matches phishing-clone lexical profile")
    if ip_changed:
        concepts.append("ip_changed: true → source IP changed mid-session")
    if mac_changed:
        concepts.append("mac_changed: true → device MAC changed mid-session")
    if oem_mismatch:
        concepts.append("mac_oem_mismatch: true → MAC vendor block (OUI) changed — spoofed hardware")
    if behavioral > 0.5:
        concepts.append(f"behavioral_drift: {behavioral:.2f} → keystroke/mouse rhythm diverged from enrolled baseline")
    if txn_score > 0.6:
        concepts.append(f"transaction_risk: {txn_score:.2f} → high-value / new-recipient transfer pattern")
    if net.get("risk_score", 0.0) >= 0.7:
        concepts.append(f"network_risk: {net.get('risk_score'):.2f} → {'; '.join(net.get('explanations', [])[-1:])}")

    # ── Classify (concept → class), highest severity wins ─────────────────────
    candidates = []
    if ip_changed and mac_changed:
        candidates.append("MITM")
    if ip_changed and oem_mismatch:
        candidates.append("session_hijack")
    if url_score > 60:
        candidates.append("phishing")
    if behavioral > 0.5:
        candidates.append("behavioral_anomaly")
    attack_type = max(candidates, key=lambda a: _SEVERITY[a]) if candidates else "clean"
    # The reasoning layer explains the DECISION. If the engine allowed the action
    # (tier 1), the headline class must not claim an attack — a weak concept that
    # fired below the action threshold stays visible in triggered_concepts, but
    # the label matches what the system actually did.
    if tier <= 1:
        attack_type = "clean"

    # confidence = how strongly the deciding concept fired
    conf_map = {"MITM": max(fp.get("risk_score", 0.9), 0.9),
                "session_hijack": max(fp.get("risk_score", 0.85), 0.85),
                "phishing": url_score / 100.0,
                "behavioral_anomaly": behavioral,
                "clean": round(1.0 - result.overall_risk, 3)}
    confidence = round(float(conf_map.get(attack_type, result.confidence)), 3)

    crypto_action = ("upgrade_SHA512_MLKEM" if tier >= 4 else
                     "upgrade_SHA512" if tier == 3 else "maintain_AES")

    action_phrase = {1: "access granted, monitoring", 2: "step-up OTP challenge issued",
                     3: "re-authentication forced, session key upgraded to SHA-512",
                     4: "session contained, post-quantum X-Wing/ML-KEM-768 key activated"}[tier]
    evidence = "; ".join(c.split(" → ")[0] for c in concepts) or "no anomalous concepts"
    if attack_type == "clean":
        summary = f"No attack detected ({evidence}). Tier {tier}: {action_phrase}."
    else:
        summary = f"{attack_type.replace('_', ' ').upper()} detected — evidence: {evidence}. Tier {tier}: {action_phrase}."

    return {
        "attack_type": attack_type,
        "confidence": confidence,
        "triggered_concepts": concepts,
        "tier_response": tier,
        "crypto_action": crypto_action,
        "summary": summary,
    }


def concept_contributions(reasoning: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Adapt reasoning concepts into the {feature,value,contribution,direction}
    shape explain.make_chart expects, so BEACON's neural provider (which has no
    feature_importances_) still gets an explainability bar chart."""
    out = []
    for c in reasoning.get("triggered_concepts", []):
        name = c.split(":")[0].strip()
        out.append({"feature": name, "value": 1, "contribution": 1.0, "direction": "risk"})
    return out[:5]
