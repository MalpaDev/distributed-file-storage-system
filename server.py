import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import argparse
import requests

# Configuration
PRIMARY_BY_FILE = {
    "file1.txt": "NY",
    "file2.txt": "TO",
    "file3.txt": "LD"
}

ALL_SERVERS = {
    "NY": "http://localhost:5001",
    "TO": "http://localhost:5002",
    "LD": "http://localhost:5003"
}

QUORUM_REQUIRED = 2

# HTTP Handler
class DataCenterHandler(BaseHTTPRequestHandler):
    server_name = "UNKNOWN"
    storage_path = ""

    # GET requests
    def do_GET(self):
        if self.path == "/ping":
            return self.send_json(200, {
                "status": "ok",
                "datacenter": self.server_name
            })

        # GET /files/<filename>
        if self.path.startswith("/files/"):
            filename = self.path.replace("/files/", "")
            filepath = os.path.join(self.storage_path, filename)

            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    content = f.read()
                return self.send_json(200, {
                    "filename": filename,
                    "content": content,
                    "datacenter": self.server_name
                })

            return self.send_json(404, {
                "error": "file not found",
                "filename": filename
            })

        # GET /vote/<filename>
        if self.path.startswith("/vote/"):
            filename = self.path.replace("/vote/", "")
            return self.send_json(200, {
                "vote": "yes",
                "filename": filename,
                "server": self.server_name
            })

        self.send_json(404, {"error": "invalid endpoint"})

    # POST requests
    def do_POST(self):
        # client write (primary only)
        if self.path.startswith("/write/"):
            return self.handle_write()

        # internal replication
        if self.path.startswith("/replicate/"):
            return self.handle_replication()

        self.send_json(404, {"error": "invalid POST endpoint"})

    # Handle replication from primary
    def handle_replication(self):
        filename = self.path.replace("/replicate/", "")

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode()
        data = json.loads(body)

        content = data.get("content")
        if content is None:
            return self.send_json(400, {"error": "missing 'content'"})

        filepath = os.path.join(self.storage_path, filename)
        with open(filepath, "w") as f:
            f.write(content)

        return self.send_json(200, {
            "status": "replicated",
            "filename": filename,
            "server": self.server_name
        })

    # Handle primary write + quorum + replication
    def handle_write(self):
        filename = self.path.replace("/write/", "")
        primary_dc = PRIMARY_BY_FILE.get(filename)

        # Check primary role
        if primary_dc != self.server_name:
            return self.send_json(403, {
                "error": "not primary",
                "required_primary": primary_dc,
                "current_server": self.server_name
            })

        # 1. Perform quorum voting
        votes = self.collect_votes(filename)

        yes_votes = sum(1 for v in votes.values() if v.get("vote") == "yes")

        if yes_votes < QUORUM_REQUIRED:
            return self.send_json(409, {
                "error": "quorum_failed",
                "required": QUORUM_REQUIRED,
                "received": yes_votes,
                "votes": votes
            })

        # 2. Read write content
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode()
        data = json.loads(body)

        new_content = data.get("content")
        if new_content is None:
            return self.send_json(400, {"error": "missing 'content'"})

        # 3. Write to primary
        filepath = os.path.join(self.storage_path, filename)
        with open(filepath, "w") as f:
            f.write(new_content)

        # 4. Replicate to others
        replication_results = self.replicate_to_others(filename, new_content)

        return self.send_json(200, {
            "status": "write and replicate successful",
            "filename": filename,
            "primary": self.server_name,
            "votes": votes,
            "replication_results": replication_results
        })

    # Quorum voting
    def collect_votes(self, filename):
        results = {}

        for dc, base_url in ALL_SERVERS.items():

            # Self-vote shortcut: always YES
            if dc == self.server_name:
                results[dc] = {"vote": "yes", "server": self.server_name}
                continue

            vote_url = f"{base_url}/vote/{filename}"

            try:
                r = requests.get(vote_url, timeout=2)
                results[dc] = r.json()
            except Exception as e:
                results[dc] = {"vote": "no", "error": str(e)}

        return results

    # Replication
    def replicate_to_others(self, filename, content):
        results = {}

        for dc, url in ALL_SERVERS.items():
            if dc == self.server_name:
                continue

            replicate_url = f"{url}/replicate/{filename}"

            try:
                r = requests.post(replicate_url, json={"content": content}, timeout=2)
                results[dc] = r.json()
            except Exception as e:
                results[dc] = {"error": str(e)}

        return results

    # Helper: send JSON response
    def send_json(self, status, obj):
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(obj).encode())
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # Client disconnected before we finished sending
            pass

# Server startup
def run_server(name, port):
    storage_path = os.path.join("files", name)
    os.makedirs(storage_path, exist_ok=True)

    DataCenterHandler.server_name = name
    DataCenterHandler.storage_path = storage_path

    server = HTTPServer(("localhost", port), DataCenterHandler)
    print(f"[{name}] Server running on port {port} | Storage: {storage_path}")
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dc", required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    run_server(args.dc, args.port)