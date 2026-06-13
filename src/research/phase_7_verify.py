import os
from datetime import datetime

def print_dir(path):
    print(f"\n--- Listing: {path} ---")
    if not os.path.exists(path):
        print("Directory does not exist.")
        return
    for f in os.listdir(path):
        fp = os.path.join(path, f)
        if os.path.isfile(fp):
            size = os.path.getsize(fp)
            ctime = datetime.fromtimestamp(os.path.getctime(fp)).strftime('%Y-%m-%d %H:%M:%S')
            print(f"{fp} | Size: {size} bytes | Created: {ctime}")

if __name__ == "__main__":
    print_dir("models")
    print_dir("reports/research")
