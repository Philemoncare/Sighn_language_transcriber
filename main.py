import os
import sys

# Shortcut to launch the AI Orchestration Layer from the root
if __name__ == "__main__":
    import os
    import sys
    import uvicorn

    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(project_root)

    # Change directory to the root to ensure relative paths for logs/db work as expected
    os.chdir(project_root)

    print("--- Signly Launcher ---")
    try:
        from ai_orchestration.main import app
        import uvicorn
        # Standard uvicorn execution
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        print(f"FATAL ERROR during startup: {e}")
        import traceback
        traceback.print_exc()
