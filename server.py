import http.server
import socketserver
import os
import json
import argparse
import requests

# GLOBAL CONFIG
DATA_DIR = "files"

# Each server is launched with a datacenter name (NY/TO/LD)
CURRENT_DC = None
CURRENT_PORT = None

SERVERS = {
    "NY": "http://localhost:5001",
    "TO": "http://localhost:5002",
    "LD": "http://localhost:5003"
}

# File → Primary DC mapping (assignment requirement)
FILE_PRIMARY = {
    "file1.txt": "NY",
    "file2.txt": "TO",
    "file3.txt": "LD"
}


# HELPER FUNCTIONS
def ensure_dc_directory(dc):
    # Make sure files/NY, files/TO, files/LD exist
    path = os.path.join(DATA_DIR, dc)
    os.makedirs(path, exist_ok=True)
    return path


def file_path(dc, filename):
    # Return full file path for this datacenter
    dc_dir = ensure_dc_directory(dc)
    return os.path.join(dc_dir, filename)


def send_replication(dc, filename, content):
    # Send file content to replica server
    url = f"{SERVERS[dc]}/replicate/{filename}"
    try:
        resp = requests.post(url, json={"content": content}, timeout=10)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def send_vote(dc, filename):
    # Request vote for quorum
    url = f"{SERVERS[dc]}/vote/{filename}"
    try:
        resp = requests.get(url, timeout=10)
        return resp.json()
    except Exception as e:
        return {"vote": "no", "error": str(e)}


# HTTP REQUEST HANDLER
class DistributedHandler(http.server.SimpleHTTPRequestHandler):

    # Utility for sending JSON
    def send_json(self, code, obj):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

    # GET request handler
    def do_GET(self):
        # Ping (used by your tests)
        if self.path == "/ping":
            return self.send_json(200, {"status": "ok", "datacenter": CURRENT_DC})

        # Quorum vote
        if self.path.startswith("/vote/"):
            filename = self.path.replace("/vote/", "")
            return self.handle_vote(filename)

        # Read file
        if self.path.startswith("/read/"):
            filename = self.path.replace("/read/", "")
            return self.handle_read(filename)

        return self.send_json(404, {"error": "unknown GET endpoint"})

    # POST request handler
    def do_POST(self):
        if self.path.startswith("/write/"):
            filename = self.path.replace("/write/", "")
            return self.handle_write(filename)

        if self.path.startswith("/replicate/"):
            filename = self.path.replace("/replicate/", "")
            return self.handle_replication(filename)

        return self.send_json(404, {"error": "unknown POST endpoint"})

    # READ HANDLER
    def handle_read(self, filename):
        full_path = file_path(CURRENT_DC, filename)

        if not os.path.exists(full_path):
            return self.send_json(404, {"error": "file not found"})

        with open(full_path, "r") as f:
            content = f.read()

        return self.send_json(200, {
            "filename": filename,
            "content": content,
            "server": CURRENT_DC
        })

    # VOTE HANDLER (QUORUM)
    def handle_vote(self, filename):
        # Very simple: always vote yes unless something breaks
        return self.send_json(200, {"vote": "yes", "server": CURRENT_DC})

    # REPLICATION HANDLER
    def handle_replication(self, filename):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except:
            return self.send_json(400, {"error": "invalid JSON"})

        content = data.get("content", "")

        # Write replicated file locally
        full_path = file_path(CURRENT_DC, filename)
        with open(full_path, "w") as f:
            f.write(content)

        return self.send_json(200, {
            "status": "replicated",
            "filename": filename,
            "server": CURRENT_DC
        })

    # WRITE HANDLER (PRIMARY → REPLICAS)
    def handle_write(self, filename):
        # Read content
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except:
            return self.send_json(400, {"error": "invalid JSON"})

        content = data.get("content", "")

        # Determine primary
        primary = FILE_PRIMARY.get(filename)
        if primary != CURRENT_DC:
            return self.send_json(403, {
                "error": "writes must go to primary",
                "expected_primary": primary,
                "this_server": CURRENT_DC
            })

        # QUORUM VOTING
        votes = {}
        yes_count = 1  # primary always counts itself
        votes[CURRENT_DC] = {"vote": "yes", "server": CURRENT_DC}

        for dc in SERVERS.keys():
            if dc == CURRENT_DC:
                continue  # avoid self-deadlock

            vote = send_vote(dc, filename)
            votes[dc] = vote

            if vote.get("vote") == "yes":
                yes_count += 1

        # Quorum requires 2 total
        if yes_count < 2:
            return self.send_json(500, {
                "status": "quorum failed",
                "votes": votes,
                "required": 2,
                "received": yes_count
            })

        # PRIMARY WRITE
        full_path = file_path(CURRENT_DC, filename)
        with open(full_path, "w") as f:
            f.write(content)

        # REPLICATION
        replication_results = {}

        for dc in SERVERS.keys():
            if dc == CURRENT_DC:
                continue
            replication_results[dc] = send_replication(dc, filename, content)

        return self.send_json(200, {
            "status": "write and replicate successful",
            "filename": filename,
            "primary": CURRENT_DC,
            "votes": votes,
            "replication_results": replication_results
        })


# SERVER STARTUP
def run_server(dc, port):
    global CURRENT_DC, CURRENT_PORT
    CURRENT_DC = dc
    CURRENT_PORT = port

    ensure_dc_directory(dc)

    with socketserver.TCPServer(("", port), DistributedHandler) as httpd:
        print(f"[{dc}] Server running on port {port}...")
        httpd.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dc", required=True)
    parser.add_argument("--port", required=True, type=int)
    args = parser.parse_args()

    run_server(args.dc, args.port)