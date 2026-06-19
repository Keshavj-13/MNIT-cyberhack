import subprocess
import time
import sys
import os
import threading

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

def _stream_output(proc, prefix):
    """Read lines from a subprocess pipe and print them with a prefix tag."""
    try:
        for line in proc.stdout:
            stripped = line.rstrip('\n').rstrip('\r')
            if stripped:
                print(f"[{prefix}] {stripped}", flush=True)
    except (ValueError, OSError):
        # Pipe closed — process exited
        pass

def run():
    print("[SYSTEM] Cleaning up previous environments...")
    
    # Clean up all ports
    all_ports = [8000, 3000, 8001, 8002, 8003, 8004, 3001, 3002, 3003, 3004]
    for port in all_ports:
        kill_process_on_port(port)

    # Port allocation is fixed to ensure cryptographic and routing isolation:
    # 8001: Customer API, 3001: Customer UI
    # 8002: Admin API, 3002: Admin UI
    # 8003: Attacker API, 3003: Attacker UI
    # 8004: Showcase API, 3004: Showcase UI

    print("[SYSTEM] Starting MNIT Isolated Security Platform...")
    processes = []
    threads = []

    # 1. Start Backend FastAPI APIs — output streamed to console with prefixes
    backends = [
        ("Customer API", "src.api.customer_api:app", 8001),
        ("Admin API", "src.api.admin_api:app", 8002),
        ("Attacker API", "src.api.attacker_api:app", 8003),
        ("Showcase API", "src.api.showcase_api:app", 8004),
    ]

    for name, import_path, port in backends:
        print(f"[SYSTEM] Starting {name} on port {port}...")
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", import_path, "--port", str(port), "--host", "127.0.0.1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True
        )
        processes.append((name, proc))
        # Start a reader thread to stream this backend's output to the console
        t = threading.Thread(target=_stream_output, args=(proc, name), daemon=True)
        t.start()
        threads.append(t)

    # Wait for backends to boot
    time.sleep(4)

    # 2. Start Frontend Vite instances — output also streamed
    frontends = [
        ("Customer UI", "surfaces/customer/vite.config.ts", 3001),
        ("Admin UI", "surfaces/admin/vite.config.ts", 3002),
        ("Attacker UI", "surfaces/attacker/vite.config.ts", 3003),
        ("Showcase UI", "surfaces/showcase/vite.config.ts", 3004),
    ]

    for name, config_path, port in frontends:
        print(f"[SYSTEM] Starting {name} on port {port}...")
        proc = subprocess.Popen(
            ["npx.cmd", "vite", "-c", config_path, "--port", str(port), "--host", "127.0.0.1"],
            cwd="ui",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        processes.append((name, proc))
        t = threading.Thread(target=_stream_output, args=(proc, name), daemon=True)
        t.start()
        threads.append(t)

    print("\n" + "="*50)
    print("MNIT FOUR ISOLATED SURFACES RUNNING")
    print("1. Customer Bank Portal:   http://localhost:3001")
    print("2. Admin Risk Board:       http://localhost:3002")
    print("3. Attacker Simulator:     http://localhost:3003")
    print("4. Public Showcase Portal: http://localhost:3004")
    print("="*50 + "\n")

    try:
        while True:
            time.sleep(1)
            # Monitor all processes
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"[ERROR] {name} terminated unexpectedly. Purging launcher...")
                    raise KeyboardInterrupt
    except KeyboardInterrupt:
        print("\n[SYSTEM] Shutting down isolated surfaces...")
        for name, proc in processes:
            if sys.platform == "win32":
                subprocess.run(f"taskkill /F /T /PID {proc.pid}", shell=True, capture_output=True)
            else:
                proc.terminate()
        print("[SYSTEM] Teardown complete.")

if __name__ == "__main__":
    run()

