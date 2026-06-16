import json
import os
import sys

# Add root folder to sys.path
sys.path.append(os.getcwd())

from src.api.internal.session_crypto import decrypt_aes_gcm

def main():
    json_path = 'scratch/crypto_exchange.json'
    if not os.path.exists(json_path):
        print(f"ERROR: {json_path} not found.")
        sys.exit(1)
        
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    print("Python reading encrypted data from JS...")
    print(f"Ciphertext (B64): {data['ciphertext_b64']}")
    print(f"Nonce (B64): {data['nonce_b64']}")
    print(f"Tag (B64): {data['tag_b64']}")
    print(f"Key (B64): {data['key_b64']}")
    
    # Run decryption using the server side decrypt function
    decrypted = decrypt_aes_gcm(
        data['ciphertext_b64'],
        data['nonce_b64'],
        data['tag_b64'],
        data['key_b64']
    )
    
    print("\n--- Decryption Result ---")
    print(f"Decrypted text: '{decrypted}'")
    print(f"Expected text:  '{data['plaintext']}'")
    
    if decrypted == data['plaintext']:
        print("\nSUCCESS: JS SubtleCrypto and Python hashlib/hmac are 100% equivalent!")
        sys.exit(0)
    else:
        print("\nFAILURE: Decrypted text does not match!")
        sys.exit(1)

if __name__ == "__main__":
    main()
