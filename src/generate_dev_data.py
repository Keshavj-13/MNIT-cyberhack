import os
import pandas as pd
import numpy as np

def generate_synthetic_banking_data(n_rows=5000):
    print(f"[INFO] Generating {n_rows} rows of synthetic banking data for development...")
    np.random.seed(42)
    from datetime import datetime, timedelta
    start_date = datetime(2023, 1, 1)
    timestamps = [start_date + timedelta(minutes=np.random.randint(0, 525600)) for _ in range(n_rows)]
    data = {
        "timestamp": timestamps,
        "customer_id": np.random.randint(1000, 2000, n_rows),
        "account_id": np.random.randint(5000, 6000, n_rows),
        "amount": np.random.uniform(1, 10000, n_rows),
        "currency": np.random.choice(["USD", "EUR", "GBP"], n_rows),
        "transaction_type": np.random.choice(["TRANSFER", "PAYMENT", "CASH_OUT"], n_rows),
        "merchant_category": np.random.choice(["RETAIL", "ENTERTAINMENT", "FOOD", "ELECTRONICS"], n_rows),
        "recipient_id": np.random.randint(1000, 9000, n_rows),
        "is_fraud": np.random.choice([0, 1], n_rows, p=[0.98, 0.02]),
        "device_id": [f"dev_{np.random.randint(1, 500)}" for _ in range(n_rows)],
        "ip_address": [f"192.168.1.{np.random.randint(1, 255)}" for _ in range(n_rows)],
        "country": np.random.choice(["USA", "UK", "CAN", "GER", "FRA"], n_rows),
        "account_age_days": np.random.randint(1, 3650, n_rows),
    }
    df = pd.DataFrame(data)
    df.to_csv(os.path.join("data/raw", "Synthetic_Multi_Pattern_Banking_Transaction_Dataset.csv"), index=False)
    print("[SUCCESS] Synthetic banking data generated.")

def generate_synthetic_network_data(n_rows=5000):
    print(f"[INFO] Generating {n_rows} rows of synthetic network data for development...")
    np.random.seed(42)
    data = {
        "Destination Port": np.random.randint(0, 65535, n_rows),
        "Flow Duration": np.random.randint(1, 1000000, n_rows),
        "Total Fwd Packets": np.random.randint(1, 100, n_rows),
        "Total Backward Packets": np.random.randint(1, 100, n_rows),
        "Fwd Packet Length Max": np.random.uniform(0, 1500, n_rows),
        "Bwd Packet Length Max": np.random.uniform(0, 1500, n_rows),
        "Flow Bytes/s": np.random.uniform(0, 10**6, n_rows),
        "Flow Packets/s": np.random.uniform(0, 10**4, n_rows),
        "Label": np.random.choice(["BENIGN", "DDoS", "PortScan", "Bot"], n_rows, p=[0.8, 0.1, 0.05, 0.05])
    }
    df = pd.DataFrame(data)
    df.to_csv(os.path.join("data/raw", "CICIDS2017_sample.csv"), index=False)
    print("[SUCCESS] Synthetic network data generated.")

if __name__ == "__main__":
    os.makedirs("data/raw", exist_ok=True)
    generate_synthetic_banking_data()
    generate_synthetic_network_data()
