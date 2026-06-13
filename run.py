import subprocess
import time
import sys
import os
import socket
import signal

def find_free_port(start_port):
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except socket.error:
                port += 1
                if port > start_port + 100:
                    raise Exception("Could not find a free port in range.")

def kill_process_on_port(port):
    if sys.platform == "win32":
        try:
            output = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True).decode()
            for line in output.strip().split('\n'):
                parts = line.split()
                if len(parts) > 4 and parts[1].endswith(f":{port}"):
                    pid = parts[-1]
                    print(f"[CLEANUP] Killing process {pid} on port {port}")
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
        except subprocess.CalledProcessError:
            pass
    else:
        subprocess.run(f"fuser -k {port}/tcp", shell=True, capture_output=True)

def run():
    print("[SYSTEM] Cleaning up previous environment...")
    
    # 1. Kill old processes
    kill_process_on_port(8080)
    kill_process_on_port(3000)

    # 2. Garbage handling: Remove old DB if it's corrupted or reset is needed
    # if os.path.exists("security_platform.db"):
    #    os.remove("security_platform.db")

    # 3. Dynamic Port Allocation
    backend_port = find_free_port(8080)
    frontend_port = find_free_port(3000)
    
    backend_url = f"http://localhost:{backend_port}"
    print(f"[SYSTEM] Backend allocated to: {backend_url}")
    print(f"[SYSTEM] Frontend allocated to: http://localhost:{frontend_port}")

    # 4. Generate dynamic config for Frontend (Vite .env)
    with open("ui/.env.local", "w") as f:
        f.write(f"VITE_API_BASE={backend_url}\n")
    
    # 5. Start Backend
    print(f"[SYSTEM] Starting FastAPI Backend on port {backend_port}...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.server:app", "--port", str(backend_port), "--host", "127.0.0.1"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=True
    )

    # 6. Wait for backend
    time.sleep(3)

    # 7. Start Frontend
    print(f"[SYSTEM] Starting Vite Frontend on port {frontend_port}...")
    os.chdir("ui")
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev", "--", "--port", str(frontend_port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=True
    )

    print("\n" + "="*40)
    print("MNIT SECURITY PLATFORM IS RUNNING")
    print(f"URL: http://localhost:{frontend_port}")
    print("="*40 + "\n")

    try:
        while True:
            time.sleep(1)
            # Optional: check if procs are alive
            if backend_proc.poll() is not None:
                print("[ERROR] Backend died. Check logs.")
                break
            if frontend_proc.poll() is not None:
                print("[ERROR] Frontend died. Check logs.")
                break
    except KeyboardInterrupt:
        print("\n[SYSTEM] Shutting down...")
        if sys.platform == "win32":
            subprocess.run(f"taskkill /F /T /PID {backend_proc.pid}", shell=True)
            subprocess.run(f"taskkill /F /T /PID {frontend_proc.pid}", shell=True)
        else:
            backend_proc.terminate()
            frontend_proc.terminate()

if __name__ == "__main__":
    run()
