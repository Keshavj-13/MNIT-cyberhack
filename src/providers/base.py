from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class RiskResult(BaseModel):
    provider_name: str
    risk_score: float  # 0.0 to 1.0
    confidence: float # 0.0 to 1.0
    severity: str     # LOW, MEDIUM, HIGH, CRITICAL
    explanations: List[str]
    raw_features: Dict[str, Any]

class RiskProvider(ABC):
    @abstractmethod
    def evaluate(self, input_data: Dict[str, Any]) -> RiskResult:
        pass
