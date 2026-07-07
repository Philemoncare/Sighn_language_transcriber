import os
import sys
import subprocess
import time

def launch():
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    print("==============================================")
    print("   Signly Neural Forge - Full System Starter  ")
    print("==============================================")

    # 1. Start the Worker (in a new window)
    # This also handles starting Redis automatically
    print("[1/2] Launching AI Worker node (and Redis)...")
    subprocess.Popen(
        [sys.executable, "worker_launcher.py"],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

    # Give the worker and redis a moment to initialize
    time.sleep(3)

    # 2. Start the FastAPI Server (in a new window)
    print("[2/2] Launching API Orchestration Layer...")
    subprocess.Popen(
        [sys.executable, "main.py"],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

    print("\nSUCCESS: All systems are initiating.")
    print("- Check the new windows for logs.")
    print("- API will be available at: http://localhost:8000")
    print("- Admin Dashboard: http://localhost:8000/admin/dashboard")
    print("==============================================")

if __name__ == "__main__":
    launch()
