import subprocess
import time
import sys

SERVERS = [
    ("NY", 5001),
    ("TO", 5002),
    ("LD", 5003)
]

def start_servers():
    processes = []

    for dc, port in SERVERS:
        print(f"Starting {dc} server on port {port}...")
        p = subprocess.Popen([
            sys.executable, "server.py",
            "--dc", dc,
            "--port", str(port)
        ])
        processes.append((dc, p))
        time.sleep(0.2)

    print("\nAll servers launched! Press Ctrl+C to stop everything.\n")

    try:
        # keep the main process alive with a simple sleep loop
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping all servers (terminate only)...")
        for dc, p in processes:
            try:
                if p.poll() is None:
                    print(f"Terminating {dc} (pid={p.pid})...")
                    p.terminate()
                else:
                    print(f"{dc} already exited.")
            except Exception as e:
                print(f"Error terminating {dc}: {e}")

        print("Terminate signals sent. Exiting launcher.")
        sys.exit(0)

if __name__ == "__main__":
    start_servers()