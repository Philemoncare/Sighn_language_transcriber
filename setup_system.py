import subprocess
import sys
import os

def check_python_version():
    version = sys.version_info
    print(f"Current Python version: {version.major}.{version.minor}.{version.micro}")
    if version.major == 3 and version.minor >= 13:
        print("WARNING: Python 3.13+ detected. AI libraries like TensorFlow and MediaPipe may not be fully compatible yet.")
        print("Recommended version: Python 3.10 or 3.11")
        return False
    return True

def create_venv():
    if os.path.exists("venv"):
        print("Virtual environment 'venv' already exists.")
    else:
        print("Creating virtual environment...")
        try:
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            print("Virtual environment created successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error creating virtual environment: {e}")

def install_dependencies():
    print("Attempting to install dependencies...")
    pip_path = os.path.join("venv", "Scripts", "pip") if os.name == "nt" else os.path.join("venv", "bin", "pip")

    if not os.path.exists(pip_path):
        pip_path = "pip" # Fallback to system pip if venv not used correctly

    try:
        # Install basic dependencies first
        basic_deps = [
            "fastapi", "uvicorn", "pydantic", "httpx", "opencv-python",
            "sqlalchemy", "psycopg2-binary", "speechrecognition",
            "pyttsx3", "python-multipart", "python-jose[cryptography]",
            "passlib[bcrypt]", "python-dotenv", "spacy"
        ]
        subprocess.run([sys.executable, "-m", "pip", "install"] + basic_deps, check=True)

        print("\nAttempting to download spaCy model...")
        subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)

        print("\nNote: TensorFlow and MediaPipe installation might fail on Python 3.14.")
        print("Attempting to install remaining AI libraries...")
        ai_deps = ["mediapipe", "tensorflow"]
        subprocess.run([sys.executable, "-m", "pip", "install"] + ai_deps)

    except subprocess.CalledProcessError as e:
        print(f"Dependency installation encountered issues: {e}")

if __name__ == "__main__":
    print("--- Sign Language Translation System Setup ---")
    is_compatible = check_python_version()
    create_venv()
    install_dependencies()

    print("\n--- Setup Complete ---")
    print("To start the system:")
    print("1. Start AI Orchestration: python ai_orchestration/main.py")
    print("2. Start API Gateway: python -m uvicorn ui_layer.api_gateway.gateway:app --port 8001")
    print("-----------------------")
