import sys
import os
# Add src to path
sys.path.append(os.getcwd())

from src.providers.implementations import (
    TransactionRiskProvider, 
    SocialEngineeringRiskProvider, 
    NetworkRiskProvider, 
    AccountTakeoverProvider
)

def test_providers():
    print("Testing Provider Initialization and Evaluation...")
    
    providers = [
        TransactionRiskProvider(),
        SocialEngineeringRiskProvider(),
        NetworkRiskProvider(),
        AccountTakeoverProvider()
    ]
    
    sample_data = {
        "amount": 500,
        "sms_text": "Please verify your account at http://evil.com",
        "H.period": 0.15,
        "BIFLOW_DIRECTION": 1,
        "income": 0.8
    }
    
    for p in providers:
        print(f"\n--- Testing {p.__class__.__name__} ---")
        print(f"Model Info: {p.model_info}")
        res = p.evaluate(sample_data)
        print(f"Result: Score={res.risk_score}, Severity={res.severity}")
        print(f"Explanations: {res.explanations}")

if __name__ == "__main__":
    test_providers()
