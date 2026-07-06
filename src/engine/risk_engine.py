from typing import List, Dict, Any
import yaml
import os
from src.providers.base import RiskProvider, RiskResult
from pydantic import BaseModel

class EngineResult(BaseModel):
    overall_risk: float
    decision: str
    escalation_level: int
    confidence: float
    provider_breakdown: Dict[str, RiskResult]
    recommendation: str
    why_decision: str

from src.engine.session_models import SessionEvent

class RiskEngine:
    def __init__(self, providers: List[RiskProvider], config_path: str = "config/risk_weights.yaml"):
        self.providers = providers
        self.weights = self._load_weights(config_path)
        self._normalize_weights()

    def _load_weights(self, path: str) -> Dict[str, float]:
        if os.path.exists(path):
            with open(path, "r") as f:
                return yaml.safe_load(f).get("weights", {})
        # Default weights
        return {
            "TransactionRiskProvider": 0.4,
            "BeaconBehavioralProvider": 0.2,
            "SocialEngineeringRiskProvider": 0.2,
            "NetworkRiskProvider": 0.1,
            "DeviceTrustProvider": 0.1
        }

    def _normalize_weights(self):
        """Normalize weights to sum to 1.0 over the providers actually registered.

        The default weight table only covers 5 providers and sums to 1.0; any
        additional registered provider (e.g. NetworkRisk, BehavioralBiometrics,
        AuthenticationRisk) falls back to 0.05, pushing the true total to 1.15.
        That diluted every confidence/risk score by ~13%. Normalizing here keeps
        relative provider importance intact while restoring total_weight == 1.0.
        """
        raw = {p.__class__.__name__: self.weights.get(p.__class__.__name__, 0.05) for p in self.providers}
        total = sum(raw.values())
        if total > 0:
            self.weights = {name: w / total for name, w in raw.items()}
        else:
            self.weights = raw

    def _load_settings(self) -> Dict[str, Any]:
        path = "config/risk_settings.json"
        defaults = {
            "threshold_challenge": 0.2,
            "threshold_restrict": 0.4,
            "threshold_contain": 0.7,
            "max_transfer_limit": 5000,
            "trust_recovery_speed": 1.0,
            "weights": {
                "TransactionRiskProvider": 0.4,
                "BeaconBehavioralProvider": 0.2,
                "SocialEngineeringRiskProvider": 0.2,
                "NetworkRiskProvider": 0.1,
                "DeviceTrustProvider": 0.1
            }
        }
        if os.path.exists(path):
            try:
                import json
                with open(path, "r") as f:
                    data = json.load(f)
                    for k, v in defaults.items():
                        if k not in data:
                            data[k] = v
                    return data
            except Exception:
                pass
        return defaults

    def evaluate_all(self, input_data: Dict[str, Any], history: List[SessionEvent] = []) -> EngineResult:
        settings = self._load_settings()
        weights_map = settings.get("weights", {})
        
        results = {}
        weighted_score = 0.0
        weighted_conf = 0.0
        
        # 1. Contextual Weight Adjustment
        current_weights = {p.__class__.__name__: weights_map.get(p.__class__.__name__, 0.05) for p in self.providers}
        
        # Re-normalize adjusted weights
        w_sum = sum(current_weights.values())
        if w_sum > 0:
            current_weights = {k: v / w_sum for k, v in current_weights.items()}
            
        limit = settings.get("max_transfer_limit", 5000)
        if input_data.get("amount", 0) > limit or input_data.get("is_new_beneficiary"):
            if "TransactionRiskProvider" in current_weights:
                current_weights["TransactionRiskProvider"] *= 1.5
        
        # Re-normalize adjusted weights
        w_sum = sum(current_weights.values())
        if w_sum > 0:
            current_weights = {k: v / w_sum for k, v in current_weights.items()}

        # 2. Evaluate all providers
        contributions = []
        for provider in self.providers:
            res = provider.evaluate(input_data)
            name = provider.__class__.__name__
            results[name] = res
            
            weight = current_weights.get(name, 0.0)
            weighted_score += res.risk_score * weight
            weighted_conf += res.confidence * weight
            contributions.append((name, res.risk_score * weight))
            
        # 3. Explainability: Identify Primary Driver
        contributions.sort(key=lambda x: x[1], reverse=True)
        primary_driver, primary_impact = contributions[0] if contributions else ("None", 0.0)
        
        # 4. Confidence Adjustment
        primary_res = results.get(primary_driver)
        final_conf = weighted_conf
        if primary_res and primary_res.confidence < 0.5 and primary_res.risk_score > 0.5:
            final_conf *= (1.0 - (primary_res.risk_score * 0.5))

        # 4b. Session prior — blend elevated baseline from current risk level
        prior = float(input_data.get("session_prior_risk", 0.0))
        if prior > 0:
            weighted_score = min(1.0, weighted_score + prior * (1.0 - weighted_score))

        # 5. Stateful Correlation (Attack Chain Multipliers)
        final_score, correlation_expl = self._apply_correlation(weighted_score, results, history)
        
        # 6. Final Decision Logic
        summary_expl = f"Primary risk factor: {primary_driver} (Impact: {primary_impact:.2f})."
        if correlation_expl:
            summary_expl = f"{correlation_expl} {summary_expl}"
            
        return self._make_decision(final_score, final_conf, results, summary_expl, settings)

    def _apply_correlation(self, base_score: float, current_results: Dict[str, RiskResult], history: List[SessionEvent]) -> tuple:
        score = base_score
        expl = ""

        # 1. Detection of LURE -> HOOK / EXPLOIT transition
        # Use each historical event's per-category provider sub-score
        # (category_scores), not the aggregate weighted overall_risk
        # (e.risk_score). A single provider's contribution to overall_risk is
        # capped by its weight (e.g. SocialEngineering's ~0.17), so the
        # aggregate can never exceed 0.7 from one category alone and this
        # check could never fire.
        # ponytail: 0.5 not 0.7 — providers score 0.5-0.9 on real attacks; 0.7 never fired
        has_recent_lure = any(e.category_scores.get("LURE", 0.0) > 0.5 for e in history[-5:])
        has_recent_hook = any(e.category_scores.get("HOOK", 0.0) > 0.5 for e in history[-5:])
        has_recent_exploit = any(e.category_scores.get("EXPLOIT", 0.0) > 0.5 for e in history[-5:])

        current_cats = [r.event_category for r in current_results.values() if r.risk_score > 0.5]

        narrative = []

        if has_recent_lure and ("HOOK" in current_cats or "EXPLOIT" in current_cats):
            score = min(1.0, score * 1.3)
            narrative.append("Risk elevated due to sequence: Previous phishing/social-engineering LURE followed by credential interaction.")

        if (has_recent_lure or has_recent_hook) and "MONETIZE" in current_cats:
            score = min(1.0, score * 1.5)
            narrative.append("CRITICAL: Transaction attempt following confirmed Attack Chain (Lure/Hook).")

        # 2. EXPLOIT -> MONETIZE transition (account takeover, no smishing precursor):
        # a session already flagged as compromised (impossible travel, rooted
        # device, etc.) that then attempts a monetary transfer is escalated
        # even without a preceding LURE/HOOK.
        if has_recent_exploit and "MONETIZE" in current_cats:
            score = min(1.0, score * 1.5)
            narrative.append("CRITICAL: Transaction attempt following confirmed Account Takeover (Exploit).")

        expl = " ".join(narrative)
        return score, expl

    def _make_decision(self, score: float, conf: float, breakdown: Dict[str, RiskResult], correlation_expl: str, settings: dict) -> EngineResult:
        t_challenge = settings.get("threshold_challenge", 0.2)
        t_restrict = settings.get("threshold_restrict", 0.4)
        t_contain = settings.get("threshold_contain", 0.7)
        
        if score < t_challenge:
            level = 1
            decision = "ALLOW"
            rec = "Continue monitoring."
            why = "Low overall risk score."
        elif score < t_restrict:
            level = 2
            decision = "CHALLENGE"
            rec = "Request Step-up Authentication (OTP/MFA)."
            why = "Moderate risk detected. Verification required."
        elif score < t_contain:
            level = 3
            decision = "RESTRICT"
            rec = "Block high-value transfers, freeze sensitive actions."
            why = "High suspicion. Restricting account capabilities."
        else:
            level = 4
            decision = "CONTAIN"
            rec = "Terminate session, lock account, escalate to security team."
            why = "Critical risk. Immediate containment required."
            
        if correlation_expl:
            why = f"{correlation_expl} {why}"
            
        return EngineResult(
            overall_risk=round(score, 4),
            decision=decision,
            escalation_level=level,
            confidence=round(conf, 4),
            provider_breakdown=breakdown,
            recommendation=rec,
            why_decision=why
        )
