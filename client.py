import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import os


# CONFIG
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

SERVERS = {
    "NY": "http://localhost:5001",
    "TO": "http://localhost:5002",
    "LD": "http://localhost:5003"
}

server_online = {"NY": True, "TO": True, "LD": True}

FILE_PRIMARY = {
    "file1.txt": "NY",
    "file2.txt": "TO",
    "file3.txt": "LD"
}


# GUI LOG HELPER
def gui_log(text_widget, msg):
    """Append text to GUI log box."""
    text_widget.insert(tk.END, msg + "\n")
    text_widget.see(tk.END)


# NETWORK HELPERS
def read_from_server(dc, filename, log_widget):
    if not server_online[dc]:
        gui_log(log_widget, f"[OFFLINE] {dc} offline — skipping.")
        return None, f"{dc} offline"

    url = f"{SERVERS[dc]}/read/{filename}"
    gui_log(log_widget, f"[NETWORK] GET {url}")

    try:
        resp = requests.get(url, timeout=2)
        return resp.json(), None
    except Exception as e:
        gui_log(log_widget, f"[ERROR] {dc} read failed: {e}")
        return None, str(e)


def write_to_primary(primary, filename, content, log_widget):
    if not server_online[primary]:
        return {"error": f"Primary {primary} offline"}

    url = f"{SERVERS[primary]}/write/{filename}"
    gui_log(log_widget, f"[NETWORK] POST {url}")

    try:
        resp = requests.post(url, json={"content": content}, timeout=10)
        result = resp.json()

        # Push-based invalidation
        cache_path = os.path.join(CACHE_DIR, filename)
        if os.path.exists(cache_path):
            os.remove(cache_path)
            gui_log(log_widget, f"[PUSH] Cache invalidated for {filename}")

        return result

    except Exception as e:
        return {"error": str(e)}


# READ / WRITE OPERATIONS
def read_file_gui(filename, log_widget):
    cache_path = os.path.join(CACHE_DIR, filename)

    if os.path.exists(cache_path):
        gui_log(log_widget, f"[CACHE] Loaded {filename} from cache")
        with open(cache_path, "r") as f:
            return f.read()

    data, err = read_from_server("NY", filename, log_widget)
    if err:
        return f"Error: {err}"
    if "content" not in data:
        return f"Error: {data}"

    with open(cache_path, "w") as f:
        f.write(data["content"])

    return data["content"]


def write_file_gui(filename, content, log_widget):
    primary = FILE_PRIMARY.get(filename)
    if not primary:
        return {"error": "Unknown file"}

    gui_log(log_widget, f"[WRITE] Writing {filename} → Primary = {primary}")
    result = write_to_primary(primary, filename, content, log_widget)

    # Record full debug JSON to console
    print("\n[DEBUG FULL WRITE RESULT]")
    print(json.dumps(result, indent=4))

    # GUI output
    if "status" in result and "votes" in result:
        yes_votes = sum(1 for dc, v in result["votes"].items() if v.get("vote") == "yes")
        gui_log(log_widget, f"Quorum: {yes_votes} yes votes")

        if "replication_results" in result:
            rep_ok = all(
                (v.get("status") == "replicated") for v in result["replication_results"].values()
            )
            gui_log(log_widget, f"Replication: {'OK' if rep_ok else 'Some failures'}")

        gui_log(log_widget, "Write Successful!\n")
    else:
        err_msg = result.get("error", "Unknown error")
        gui_log(log_widget, f"Write Failed: {err_msg}\n")

    return result


# GUI APPLICATION
class DistributedClientGUI:
    def __init__(self, root):
        self.root = root
        root.title("Distributed File Client")

        main_frame = ttk.Frame(root, padding=10)
        main_frame.grid(row=0, column=0, sticky="nsew")

        # SERVER ONLINE/OFFLINE PANEL
        status_frame = ttk.LabelFrame(main_frame, text="Simulated Server Status")
        status_frame.grid(row=0, column=0, sticky="ew", pady=5)

        self.var_ny = tk.BooleanVar(value=True)
        self.var_to = tk.BooleanVar(value=True)
        self.var_ld = tk.BooleanVar(value=True)

        ttk.Checkbutton(status_frame, text="NY Online", variable=self.var_ny,
                        command=self.update_server_status).grid(row=0, column=0)
        ttk.Checkbutton(status_frame, text="TO Online", variable=self.var_to,
                        command=self.update_server_status).grid(row=0, column=1)
        ttk.Checkbutton(status_frame, text="LD Online", variable=self.var_ld,
                        command=self.update_server_status).grid(row=0, column=2)

        # FILE SELECTION + READ BUTTON
        selection_frame = ttk.Frame(main_frame)
        selection_frame.grid(row=1, column=0, pady=5, sticky="ew")

        ttk.Label(selection_frame, text="File:").grid(row=0, column=0, padx=5)
        self.file_var = tk.StringVar(value="file1.txt")
        self.file_menu = ttk.Combobox(
            selection_frame, textvariable=self.file_var,
            values=["file1.txt", "file2.txt", "file3.txt"], width=15
        )
        self.file_menu.grid(row=0, column=1)

        ttk.Button(selection_frame, text="Read File",
                   command=self.read_action).grid(row=0, column=2, padx=5)

        # WRITE SECTION
        write_frame = ttk.LabelFrame(main_frame, text="Write Content")
        write_frame.grid(row=2, column=0, pady=5, sticky="ew")

        self.write_text = tk.Text(write_frame, height=4, width=50)
        self.write_text.grid(row=0, column=0, padx=5, pady=5)

        ttk.Button(write_frame, text="Write File",
                   command=self.write_action).grid(row=1, column=0, pady=5)

        # LOG OUTPUT
        log_frame = ttk.LabelFrame(main_frame, text="Logs / Output")
        log_frame.grid(row=3, column=0, pady=5, sticky="nsew")

        self.log_widget = tk.Text(log_frame, height=18, width=60)
        self.log_widget.grid(row=0, column=0, padx=5, pady=5)


    # GUI CALLBACKS
    def update_server_status(self):
        server_online["NY"] = self.var_ny.get()
        server_online["TO"] = self.var_to.get()
        server_online["LD"] = self.var_ld.get()

        gui_log(
            self.log_widget,
            f"[STATUS] NY={server_online['NY']}  TO={server_online['TO']}  LD={server_online['LD']}"
        )

    def read_action(self):
        filename = self.file_var.get()
        gui_log(self.log_widget, f"\n[READ] Requesting {filename}...\n")

        content = read_file_gui(filename, self.log_widget)

        gui_log(self.log_widget, "---- FILE CONTENT ----")
        gui_log(self.log_widget, content)
        gui_log(self.log_widget, "-----------------------\n")

    def write_action(self):
        filename = self.file_var.get()
        content = self.write_text.get("1.0", tk.END).strip()

        if not content:
            messagebox.showerror("Error", "Content cannot be empty.")
            return

        gui_log(self.log_widget, f"\n[WRITE] Writing {filename}...\n")

        write_file_gui(filename, content, self.log_widget)


if __name__ == "__main__":
    root = tk.Tk()
    app = DistributedClientGUI(root)
    root.mainloop()