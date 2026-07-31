"""Shared fixtures for reasoning-layer verification.

`make_result` synthesises the minimal EngineResult-shaped object that
build_reasoning reads, so we can drive it over the whole input space without
standing up the engine. `spec_classify` is an INDEPENDENT reference
implementation of the intended detection logic — the gold standard the real
function is diffed against.
"""
from types import SimpleNamespace
from typing import Tuple


def make_result(ip: bool, mac: bool, oem: bool, url_score: float,
                behavioral: float, tier: int):
    """Build an object with the .provider_breakdown / .escalation_level /
    .overall_risk / .confidence surface build_reasoning consumes."""
    def prov(name, score, cat="NEUTRAL"):
        return {"provider_name": name, "risk_score": score, "event_category": cat,
                "explanations": [], "severity": "LOW"}
    breakdown = {
        "URLPhishing": prov("URLPhishing", url_score / 100.0),
        "SessionFingerprint": prov("SessionFingerprint", 0.9 if (ip and mac) else 0.05,
                                   "EXPLOIT" if (ip and mac) else "NEUTRAL"),
        "BeaconBehavioral (Ensemble)": prov("BeaconBehavioral (Ensemble)", behavioral),
        "AccountTakeover": prov("AccountTakeover", 0.0),
        "TransactionRisk": prov("TransactionRisk", 0.0),
        "NetworkRisk": prov("NetworkRisk", 0.0),
    }
    return SimpleNamespace(provider_breakdown=breakdown, escalation_level=tier,
                           overall_risk=0.5, confidence=0.5)


def make_payload(ip: bool, mac: bool, oem: bool) -> dict:
    return {"ip_changed": ip, "mac_changed": mac, "mac_oem_mismatch": oem}


def spec_classify(ip: bool, mac: bool, oem: bool, url: float,
                  beh: float, tier: int) -> Tuple[str, str]:
    """Independent gold-standard reference of the intended logic."""
    candidates = []
    if ip and mac:
        candidates.append(("MITM", 4))
    if ip and oem:
        candidates.append(("session_hijack", 5))
    if url > 60:
        candidates.append(("phishing", 2))
    if beh > 0.5:
        candidates.append(("behavioral_anomaly", 3))
    attack = max(candidates, key=lambda t: t[1])[0] if candidates else "clean"
    if tier <= 1:
        attack = "clean"
    crypto = ("upgrade_SHA512_MLKEM" if tier >= 4 else
              "upgrade_SHA512" if tier == 3 else "maintain_AES")
    return attack, crypto


# The meaningful finite partition of the input space (thresholds straddled).
FLAG_COMBOS = [(ip, mac, oem) for ip in (False, True)
               for mac in (False, True) for oem in (False, True)]
URL_POINTS = [0.0, 61.0, 90.0]      # below / just above / well above 60
BEH_POINTS = [0.0, 0.6]             # below / above 0.5
TIERS = [1, 2, 3, 4]
