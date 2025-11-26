# Distributed File Storage System (Simulation)

A Python-based simulation of a distributed file storage system modeled after real-world platforms like Dropbox and Google Drive.  
This project demonstrates **primary-based replication**, **quorum enforcement**, **client-side caching**, and **push-based consistency** across multiple simulated data centers.

---

## 🚀 Features

### ✔ Multi–Data Center Architecture
Three simulated data centers:
- New York  
- Toronto  
- London  

Each server runs locally on a different port and maintains its own copy of all files.

---

### ✔ Primary-Based Replication
Each file is assigned a **primary server**, responsible for handling all write operations.

Example:
- `file1.txt` → Primary = New York  
- `file2.txt` → Primary = Toronto  
- `file3.txt` → Primary = London  

Primary updates propagate to the other replicas.

---

### ✔ Quorum-Based Conflict Resolution
Before a client can update a file:
- 2 out of 3 servers must approve the write request  
- Prevents conflicts during concurrent updates

---

### ✔ Client-Side Caching
The Tkinter client:
- Downloads frequently accessed files into a local cache  
- Detects cache validity  
- Automatically invalidates outdated local copies when servers push updates

---

### ✔ Push-Based Consistency Protocol
Whenever the primary server updates a file:
1. The primary writes the new version  
2. The primary pushes updates to the secondary replicas  
3. The primary sends cache-invalidation messages to clients  

This ensures all clients always receive the latest version.