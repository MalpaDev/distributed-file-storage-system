import os
import json
import requests
import time

CACHE_DIR = "cache"
CACHE_META = os.path.join(CACHE_DIR, "cache_metadata.json")

ALL_SERVERS = {
    "NY": "http://localhost:5001",
    "TO": "http://localhost:5002",
    "LD": "http://localhost:5003"
}

PRIMARY_BY_FILE = {
    "file1.txt": "NY",
    "file2.txt": "TO",
    "file3.txt": "LD"
}

# Cache system
def ensure_cache():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    if not os.path.exists(CACHE_META):
        with open(CACHE_META, "w") as f:
            json.dump({}, f)

def load_cache_metadata():
    with open(CACHE_META, "r") as f:
        return json.load(f)

def save_cache_metadata(meta):
    with open(CACHE_META, "w") as f:
        json.dump(meta, f, indent=4)

# GET file with caching
def get_file(filename):
    ensure_cache()
    meta = load_cache_metadata()

    cache_path = os.path.join(CACHE_DIR, filename)

    # If cached, return immediately
    if filename in meta and os.path.exists(cache_path):
        print(f"[CACHE] Returning cached version of {filename}")
        with open(cache_path, "r") as f:
            return f.read()

    # Otherwise GET file from ANY server (pick NY for simplicity)
    print(f"[NETWORK] Requesting {filename} from NY server...")
    url = f"{ALL_SERVERS['NY']}/files/{filename}"

    try:
        r = requests.get(url, timeout=2)
        if r.status_code != 200:
            print("Server error:", r.json())
            return None

        response = r.json()
        content = response["content"]

        # Save into cache
        with open(cache_path, "w") as f:
            f.write(content)

        # Update metadata
        meta[filename] = {
            "timestamp": time.time(),
            "source": "NY"
        }
        save_cache_metadata(meta)

        return content

    except Exception as e:
        print("Error fetching file:", e)
        return None

# Write file (invalidates cache)
def write_file(filename, content):
    primary_dc = PRIMARY_BY_FILE[filename]
    primary_url = ALL_SERVERS[primary_dc]

    print(f"[NETWORK] Sending write to primary ({primary_dc})...")

    try:
        r = requests.post(
            f"{primary_url}/write/{filename}",
            json={"content": content},
            timeout=10
        )
        result = r.json()

        if r.status_code != 200:
            print("Write failed:", result)
            return False

        print("Write result:", result)

        # Invalidate cache
        cache_path = os.path.join(CACHE_DIR, filename)
        if os.path.exists(cache_path):
            os.remove(cache_path)

        meta = load_cache_metadata()
        if filename in meta:
            del meta[filename]
            save_cache_metadata(meta)

        print("[CACHE] Cache invalidated for", filename)
        return True

    except Exception as e:
        print("Error writing file:", e)
        return False

# CLI menu
def menu():
    ensure_cache()

    while True:
        print("\nDistributed Client Menu")
        print("1. Read file")
        print("2. Write file")
        print("3. Exit")

        choice = input("Choose: ")

        if choice == "1":
            filename = input("Enter filename (file1.txt / file2.txt / file3.txt): ")
            content = get_file(filename)
            if content is not None:
                print("\n---- File Content ----")
                print(content)
                print("----------------------")

        elif choice == "2":
            filename = input("Enter filename to write: ")
            content = input("Enter new content: ")
            write_file(filename, content)

        elif choice == "3":
            print("Goodbye!")
            break
        else:
            print("Invalid option")


if __name__ == "__main__":
    menu()