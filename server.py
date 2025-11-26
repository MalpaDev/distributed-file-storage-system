import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import argparse

class DataCenterHandler(BaseHTTPRequestHandler):
    server_name = "UNKNOWN"
    storage_path = ""

    def do_GET(self):
        if self.path == "/ping":
            self.send_json(200, {
                "status": "ok",
                "datacenter": self.server_name
            })
            return

        # Serve files: /files/<filename>
        if self.path.startswith("/files/"):
            filename = self.path.replace("/files/", "")
            filepath = os.path.join(self.storage_path, filename)

            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    content = f.read()

                self.send_json(200, {
                    "filename": filename,
                    "content": content,
                    "datacenter": self.server_name
                })
            else:
                self.send_json(404, {
                    "error": "file not found",
                    "filename": filename,
                    "datacenter": self.server_name
                })
            return

        # Unknown route
        self.send_json(404, {"error": "invalid endpoint"})

    def send_json(self, status, obj):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

def run_server(name, port):
    # Determine file storage path for this server
    storage_path = os.path.join("files", name)

    # Auto-create directory if not exists
    os.makedirs(storage_path, exist_ok=True)

    DataCenterHandler.server_name = name
    DataCenterHandler.storage_path = storage_path

    server = HTTPServer(("localhost", port), DataCenterHandler)
    print(f"[{name}] Server running on port {port} | Storage: {storage_path}")
    server.serve_forever()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dc", required=True, help="Data center name (NY, TO, LD)")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    run_server(args.dc, args.port)