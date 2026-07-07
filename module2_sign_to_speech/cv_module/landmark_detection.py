import cv2
import numpy as np
import logging
import time
import sys

# FORCE NUMPY INITIALIZATION to prevent "no attribute floating" in broken environments
try:
    _ = np.array([1.0]).var()
except:
    pass

mp_holistic = None
mp_drawing = None
MEDIAPIPE_AVAILABLE = False

try:
    import mediapipe as mp
    try:
        import mediapipe.python.solutions.holistic as mp_holistic
        import mediapipe.python.solutions.drawing_utils as mp_drawing
    except ImportError:
        import mediapipe.solutions.holistic as mp_holistic
        import mediapipe.solutions.drawing_utils as mp_drawing
    MEDIAPIPE_AVAILABLE = True
except Exception as e:
    MEDIAPIPE_AVAILABLE = False
    print(f"CRITICAL: MediaPipe failed to load: {e}")

logger = logging.getLogger("CV_Module_Optimized")

class CVModule:
    def __init__(self, static_mode=False):
        self.active = False
        self.static_mode = static_mode
        self.holistic = None
        if MEDIAPIPE_AVAILABLE:
            self._init_holistic(static_mode)
        self.last_process_time = 0

    def _init_holistic(self, static_mode):
        try:
            if self.holistic:
                try: self.holistic.close()
                except: pass

            self.mp_holistic = mp_holistic
            self.holistic = self.mp_holistic.Holistic(
                static_image_mode=static_mode,
                model_complexity=1,
                smooth_landmarks=not static_mode,
                min_detection_confidence=0.45,
                min_tracking_confidence=0.45
            )
            self.active = True
            self.static_mode = static_mode
            logger.info(f"MediaPipe Holistic Initialized (static_mode={static_mode})")
        except Exception as e:
            logger.error(f"MediaPipe initialization failed: {e}")
            self.active = False
            self.holistic = None

    def close(self):
        if self.holistic:
            try:
                self.holistic.close()
                logger.info("MediaPipe resources released.")
            except Exception as e:
                logger.error(f"Error during MediaPipe release: {e}")
            finally:
                self.holistic = None
                self.active = False

    def set_mode(self, static_mode: bool):
        if self.static_mode != static_mode or not self.holistic:
            self._init_holistic(static_mode)

    def detect_landmarks(self, frame: np.ndarray, multi_hand=False):
        if not self.active or frame is None:
            return np.zeros(1662)

        try:
            # FORCE RE-CAST to standard numpy array to bypass Numpy 2.0 / OpenCV mismatch
            frame = np.asarray(frame, dtype=np.uint8)

            h, w = frame.shape[:2]
            if w > 1280:
                 frame = cv2.resize(frame, (1280, int(h * 1280 / w)))

            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False
            results = self.holistic.process(image)
            if multi_hand: return results
            return self._extract_keypoints(results)
        except Exception as e:
            logger.error(f"Processing Error: {e}")
            return np.zeros(1662)

    def is_blurry(self, frame, threshold=100.0):
        """
        Ultra-stable blurry detection using OpenCV directly to avoid Numpy multiarray bugs.
        """
        try:
            if frame is None: return True

            # FORCE RE-CAST
            frame_clean = np.asarray(frame, dtype=np.uint8)

            gray = cv2.cvtColor(frame_clean, cv2.COLOR_BGR2GRAY)
            lap = cv2.Laplacian(gray, cv2.CV_32F)
            # Use OpenCV for variance to bypass Numpy multiarray attribute errors
            _, stddev = cv2.meanStdDev(lap)
            variance = stddev[0][0] ** 2
            return float(variance) < threshold
        except Exception as e:
            logger.debug(f"Blurry Check Logic Error: {e}")
            return False

    def _extract_keypoints(self, results):
        pose = np.array([[res.x, res.y, res.z, res.visibility] for res in results.pose_landmarks.landmark]).flatten() if results.pose_landmarks else np.zeros(33*4)
        face = np.array([[res.x, res.y, res.z] for res in results.face_landmarks.landmark]).flatten() if results.face_landmarks else np.zeros(468*3)
        lh = np.array([[res.x, res.y, res.z] for res in results.left_hand_landmarks.landmark]).flatten() if results.left_hand_landmarks else np.zeros(21*3)
        rh = np.array([[res.x, res.y, res.z] for res in results.right_hand_landmarks.landmark]).flatten() if results.right_hand_landmarks else np.zeros(21*3)
        return np.concatenate([pose, face, lh, rh])
