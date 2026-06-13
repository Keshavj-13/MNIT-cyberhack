from pydantic import BaseModel
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
