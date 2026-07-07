import os
import sys
import subprocess
import socket
import time

def is_redis_running():
    try:
        with socket.create_connection(("localhost", 6379), timeout=1):
            return True
    except:
        return False

def start_redis():
    project_root = os.path.dirname(os.path.abspath(__file__))
    redis_exe = os.path.join(project_root, "redis", "redis-server.exe")

    if os.path.exists(redis_exe):
        print(f"Launching embedded Redis server from: {redis_exe}")
        # Start redis-server in a new window/process
        # We use a CMD wrapper to keep the window open on crash so we can see the error
        cmd = f'start "Signly-Redis" /D "{os.path.join(project_root, "redis")}" redis-server.exe'
        subprocess.Popen(cmd, shell=True)

        # Give it a few seconds to boot
        print("Waiting for Redis to initialize...")
        for i in range(10):
            if is_redis_running():
                print(f"Redis server detected on port 6379 after {i+1}s.")
                return True
            time.sleep(1)
    else:
        print(f"CRITICAL: redis-server.exe not found at {redis_exe}")
    return False

# Shortcut to launch the Celery Worker from the root
if __name__ == "__main__":
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(project_root)
    os.chdir(project_root)

    print("--- Signly Neural Forge Worker Launcher ---")

    if not is_redis_running():
        if not start_redis():
            print("WARNING: Redis is not running and couldn't be started automatically.")
            print("Requirement: Ensure Redis is running (redis-server)")
    else:
        print("Verified: Redis server is already running.")

    # Command to run celery worker
    # We use -P solo on Windows for stability with OpenCV/TensorFlow
    # Use sys.executable -m celery for better compatibility on Windows
    cmd = [
        sys.executable,
        "-m", "celery",
        "-A", "ai_orchestration.core.celery_app",
        "worker",
        "--loglevel=info",
        "-P", "solo"
    ]

    try:
        print("Launching Celery Worker...")
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nWorker shutdown requested.")
    except Exception as e:
        print(f"FATAL ERROR during worker startup: {e}")

    print("\n--- Worker Process Finished ---")
    input("Press Enter to close this window...")
