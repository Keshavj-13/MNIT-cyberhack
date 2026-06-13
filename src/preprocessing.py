import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder

RAW_DATA_PATH = "data/raw"
PROCESSED_DATA_PATH = "data/processed"

def preprocess_transaction_data():
    print("[INFO] Preprocessing Transaction data...")
    file_path = os.path.join(RAW_DATA_PATH, "Synthetic_Multi_Pattern_Banking_Transaction_Dataset.csv")
    df = pd.read_csv(file_path)
    
    # Convert timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(['customer_id', 'timestamp'])
    
    # Context Feature: Transaction Velocity (last 24h)
    # Using index as the time-based reference for rolling
    df = df.set_index('timestamp')
    df['tx_velocity_24h'] = df.groupby('customer_id')['amount'].rolling('24h').count().values
    df = df.reset_index()
    
    # Context Feature: Amount Deviation (vs customer mean)
    customer_mean = df.groupby('customer_id')['amount'].transform('mean')
    df['amount_deviation'] = df['amount'] / (customer_mean + 1e-9)
    
    # Context Feature: New Beneficiary
    df['is_new_beneficiary'] = df.groupby('customer_id')['recipient_id'].transform(
        lambda x: (~x.duplicated()).astype(int)
    )
    
    # Context Feature: Time Risk (11PM - 5AM)
    df['hour'] = df['timestamp'].dt.hour
    df['time_risk'] = ((df['hour'] >= 23) | (df['hour'] <= 5)).astype(int)
    
    # Categorical Encoding
    le = LabelEncoder()
    for col in ['currency', 'transaction_type', 'merchant_category', 'country']:
        df[col] = le.fit_transform(df[col].astype(str))
    
    # Save as Parquet
    output_path = os.path.join(PROCESSED_DATA_PATH, "transaction_data.parquet")
    df.to_parquet(output_path, index=False)
    print(f"[SUCCESS] Transaction data saved to {output_path}")

def preprocess_network_data():
    print("[INFO] Preprocessing Network data...")
    file_path = os.path.join(RAW_DATA_PATH, "CICIDS2017_sample.csv")
    df = pd.read_csv(file_path)
    
    # Simple cleaning: Replace inf with nan and drop
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(inplace=True)
    
    # Encode Labels
    le = LabelEncoder()
    df['Label_Encoded'] = le.fit_transform(df['Label'])
    
    # Save as Parquet
    output_path = os.path.join(PROCESSED_DATA_PATH, "network_data.parquet")
    df.to_parquet(output_path, index=False)
    print(f"[SUCCESS] Network data saved to {output_path}")

if __name__ == "__main__":
    os.makedirs(PROCESSED_DATA_PATH, exist_ok=True)
    preprocess_transaction_data()
    preprocess_network_data()
