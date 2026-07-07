import os
import sys
import numpy as np
import cv2

# Project setup
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from module2_sign_to_speech.cv_module.landmark_detection import CVModule

def run_test():
    print("Initializing CVModule...")
    try:
        cv = CVModule(static_mode=True)
        print(f"CVModule active: {cv.active}")

        # Create a dummy frame
        # Use a very safe way to create a numpy array that OpenCV should accept
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        print("Checking blur...")
        blurry = cv.is_blurry(frame)
        print(f"Is blurry: {blurry}")

        print("Detecting landmarks...")
        lms = cv.detect_landmarks(frame)
        print(f"Landmarks shape: {lms.shape}")

        if np.any(lms):
            print("SUCCESS: Landmarks detected (even if zero, array returned)")
        else:
            print("SUCCESS: Zero array returned (expected for black frame)")

    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test()
