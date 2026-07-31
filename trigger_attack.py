import os
os.environ['ALLOW_DEFAULT_SECRETS'] = '1'
from src.db.models import SessionLocal, CustomerSession
from src.api.attacker_api import generate_simulated_telemetry
from src.api.customer_api import telemetry

db = SessionLocal()
# Find the active session for rahul_verma
cust_session = db.query(CustomerSession).filter(CustomerSession.user_id == "rahul_verma", CustomerSession.is_active == True).first()

if cust_session:
    print(f"Found active session: {cust_session.session_id}")
    # Inject anomaly telemetry
    payload = generate_simulated_telemetry(2, True, cust_session.session_id, cust_session.aes_key)
    try:
        from src.api.attacker_api import customer_telemetry
        customer_telemetry(payload, db)
    except Exception as e:
        print("Telemetry threw:", e)
    print("Injected attack telemetry")
else:
    print("No active session found for rahul_verma")
