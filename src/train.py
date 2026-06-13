import os
import subprocess

def run_step(name, command):
    print(f"\n{'='*20} {name} {'='*20}")
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Step {name} failed: {e}")
        return False
    return True

def main():
    steps = [
        ("Data Generation", "python src/generate_dev_data.py"),
        ("Schema Inspection", "python src/inspect_schema.py"),
        ("Preprocessing", "python src/preprocessing.py"),
        ("Train Transaction Model", "python src/models/transaction_model.py"),
        ("Train Network Model", "python src/models/network_model.py"),
    ]
    
    for name, cmd in steps:
        if not run_step(name, cmd):
            break
            
    print("\n[FINISH] Project build complete. Start API with: uvicorn src.api.main:app --reload")

if __name__ == "__main__":
    main()
