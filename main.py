import subprocess
import time
import sys
import os

SERVERS = [
    ("NY", 5001),
    ("TO", 5002),
    ("LD", 5003)
]

def start_servers_and_client():
    # Keep track of (name, subprocess) tuples
    processes = []

    # Start servers
    for dc, port in SERVERS:
        print(f"Starting {dc} server on port {port}...")
        p = subprocess.Popen([
            sys.executable, "server.py",
            "--dc", dc,
            "--port", str(port)
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        processes.append((dc, p))
        # Slight delay so the console messages are readable and servers can bind ports
        time.sleep(0.2)

    print("\nAll servers launched! Press Ctrl+C to stop everything.\n")

    # Launch GUI client (does not block)
    # Use sys.executable to ensure the same Python interpreter is used
    if os.path.exists("client.py"):
        try:
            print("[MAIN] Launching Tkinter client GUI...")
            subprocess.Popen([sys.executable, "client.py"])
        except Exception as e:
            print("[MAIN] Failed to launch GUI:", e)
    else:
        print("[MAIN] client.py not found — skipping GUI auto-launch.")

    # Keep the launcher alive; on Ctrl+C we terminate child processes
    try:
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
    start_servers_and_client()