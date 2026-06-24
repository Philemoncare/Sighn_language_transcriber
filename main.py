import os
import sys

# Shortcut to launch the AI Orchestration Layer from the root
if __name__ == "__main__":
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(project_root)

    # Change directory to the root to ensure relative paths for logs/db work as expected
    os.chdir(project_root)

    print("--- SnLag Universal Core Launcher ---")
    try:
        from ai_orchestration.main import app
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except ImportError as e:
        print(f"Error: Could not find the orchestration layer. {e}")
        print("Please ensure you are running from the project root and requirements are installed.")
