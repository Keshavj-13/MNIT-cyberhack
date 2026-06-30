import unittest
import sys
import os
from fastapi.testclient import TestClient

# Add current working dir to sys.path
sys.path.append(os.getcwd())

from src.db.models import init_db, SessionLocal, CustomerSession
from src.api.customer_api import app as customer_app
from src.api.admin_api import app as admin_app
from src.api.attacker_api import app as attacker_app
from src.api.showcase_api import app as showcase_app
from src.api.internal.session_crypto import create_jwt_token, generate_aes_key, encrypt_aes_gcm

class TestSurfacesIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.db = SessionLocal()
        
    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def setUp(self):
        self.customer_client = TestClient(customer_app)
        self.admin_client = TestClient(admin_app)
        self.attacker_client = TestClient(attacker_app)
        self.showcase_client = TestClient(showcase_app)

    def test_showcase_read_only(self):
        """Showcase API must reject all write requests with 405 Method Not Allowed or 404 Not Found."""
        res = self.showcase_client.post("/showcase/models", json={"test": "data"})
        self.assertEqual(res.status_code, 405)
        
        # DELETE on a non-existent sub-resource should return 404 or 405
        res = self.showcase_client.delete("/showcase/datasets/paysim")
        self.assertIn(res.status_code, [404, 405])
        
        # Public read-only checks should succeed
        res = self.showcase_client.get("/showcase/models")
        self.assertEqual(res.status_code, 200)

    def test_admin_auth_required(self):
        """Admin API must reject unauthenticated requests with 401."""
        res = self.admin_client.get("/admin/events")
        self.assertEqual(res.status_code, 401)
        
        # Check wrong cookie name
        self.admin_client.cookies.set("customer_session", "dummy_token")
        res = self.admin_client.get("/admin/events")
        self.assertEqual(res.status_code, 401)

    def test_attacker_auth_required(self):
        """Attacker API must reject unauthenticated requests with 401."""
        res = self.attacker_client.get("/attacker/scenarios")
        self.assertEqual(res.status_code, 401)

    def test_cross_token_rejection(self):
        """JWT issued for one surface must be rejected on other surfaces."""
        # 1. Token signed with wrong secret -> raises 401 (signature verify fails)
        admin_token = create_jwt_token("admin_user", "admin", expires_in_minutes=5)
        self.customer_client.cookies.set("customer_session", admin_token)
        res = self.customer_client.get("/customer/auth/me")
        self.assertEqual(res.status_code, 401)
        
        # 2. Token signed with correct secret but wrong surface claim -> raises 403
        from src.api.internal.session_crypto import create_jwt_token as raw_create_token
        # Create token using CUSTOMER secret but stating surface="admin"
        wrong_claim_token = raw_create_token("attacker_user", "customer", expires_in_minutes=5, extra_claims={"surface": "admin"})
        self.customer_client.cookies.set("customer_session", wrong_claim_token)
        res = self.customer_client.get("/customer/auth/me")
        self.assertEqual(res.status_code, 403)

    def test_customer_response_sanitization(self):
        """Customer transfer response must NEVER leak risk scores, model details, or provider breakdowns."""
        # Establish a valid customer session
        import secrets
        session_id = f"test_eval_sid_{secrets.token_hex(4)}"
        aes_key = generate_aes_key()
        
        # Create session in DB
        cust_sess = CustomerSession(
            session_id=session_id,
            user_id="test_cust",
            aes_key=aes_key,
            risk_level=1,
            key_version=1,
            is_active=True
        )
        self.db.add(cust_sess)
        self.db.commit()
        
        # Create valid token
        token = create_jwt_token("test_cust", "customer", expires_in_minutes=5, extra_claims={"sid": session_id})
        self.customer_client.cookies.set("customer_session", token)

        # Encrypt the transfer request (use json.dumps to avoid capitalization of False)
        import json
        transfer_payload = {"amount": 100.0, "beneficiary_id": 1, "is_new_beneficiary": False}
        encrypted = encrypt_aes_gcm(json.dumps(transfer_payload), aes_key)
        
        req_body = {
            "session_id": session_id,
            "key_version": 1,
            "ciphertext": encrypted["ciphertext"],
            "nonce": encrypted["nonce"],
            "tag": encrypted["tag"]
        }

        # Run transfer
        res = self.customer_client.post("/customer/transfer", json=req_body)
        self.assertEqual(res.status_code, 200)
        
        # Response is encrypted. Decrypt it to verify fields.
        res_data = res.json()
        from src.api.internal.session_crypto import decrypt_aes_gcm
        decrypted_str = decrypt_aes_gcm(res_data["ciphertext"], res_data["nonce"], res_data["tag"], aes_key)
        decrypted_res = json.loads(decrypted_str)
        
        # Verify sanitization: must not leak internal models or scores
        self.assertIn("status", decrypted_res)
        self.assertIn("message", decrypted_res)
        self.assertNotIn("overall_risk", decrypted_res)
        self.assertNotIn("confidence", decrypted_res)
        self.assertNotIn("provider_breakdown", decrypted_res)
        self.assertNotIn("why_decision", decrypted_res)
        self.assertNotIn("TransactionRiskProvider", decrypted_res)

        # Clean up
        self.db.delete(cust_sess)
        self.db.commit()

    def test_telemetry_triggers_evaluation(self):
        """Telemetry batches must invoke risk evaluation and rotate the live session when warranted."""
        import secrets
        from types import SimpleNamespace
        from unittest.mock import patch
        from src.db.models import TelemetryData

        session_id = f"test_tel_sid_{secrets.token_hex(4)}"
        aes_key = generate_aes_key()
        cust_sess = CustomerSession(
            session_id=session_id,
            user_id="test_cust",
            aes_key=aes_key,
            risk_level=1,
            key_version=1,
            is_active=True
        )
        self.db.add(cust_sess)
        self.db.commit()

        events = [
            {"type": "session", "timestamp": 1000, "data": {"event": "page_load", "url": "https://bank.example/home"}},
            {"type": "keystroke", "timestamp": 1100, "data": {"event": "dwell", "dwellTime": 120, "key": "a"}},
            {"type": "mouse", "timestamp": 1200, "data": {"event": "move", "x": 10, "y": 20, "velocity": 2.5}},
        ]

        with patch("src.api.customer_api.run_evaluation", return_value=SimpleNamespace(escalation_level=3)) as mocked_eval:
            res = self.customer_client.post("/customer/telemetry", json={"session_id": session_id, "events": events})

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["count"], len(events))
        self.assertTrue(mocked_eval.called)

        self.db.refresh(cust_sess)
        self.assertEqual(cust_sess.risk_level, 3)
        self.assertEqual(cust_sess.key_version, 2)
        self.assertNotEqual(cust_sess.aes_key, aes_key)
        self.assertEqual(self.db.query(TelemetryData).filter(TelemetryData.session_id == session_id).count(), len(events))

        self.db.query(TelemetryData).filter(TelemetryData.session_id == session_id).delete()
        self.db.delete(cust_sess)
        self.db.commit()

if __name__ == "__main__":
    unittest.main()
