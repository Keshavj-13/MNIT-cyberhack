from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any, List

class SessionEvent(BaseModel):
    user_id: str
    session_id: str
    event_category: str
    timestamp: datetime
    risk_score: float
    confidence: float
    explanations: List[str]
    input_payload: Dict[str, Any]
    # Per-provider {event_category: max risk_score} for this event, derived from
    # provider_breakdown. Lets correlation logic check category-specific evidence
    # instead of the aggregate (weighted) overall_risk.
    category_scores: Dict[str, float] = Field(default_factory=dict)
