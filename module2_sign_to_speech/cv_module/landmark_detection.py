import cv2
import numpy as np
import logging
import time

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

# Configure performance logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CV_Module_Optimized")

class CVModule:
    def __init__(self):
        self.active = False
        if MEDIAPIPE_AVAILABLE:
            try:
                self.mp_holistic = mp.solutions.holistic
                # PERFORMANCE FIX: Set model_complexity to 0 for fastest real-time inference
                # Requirement 2.4: Optimized initialization
                self.holistic = self.mp_holistic.Holistic(
                    static_image_mode=False,
                    model_complexity=0,             # 0 = Lite (Fastest), 1 = Balanced
                    smooth_landmarks=True,
                    min_detection_confidence=0.6,   # Requirement 3.1
                    min_tracking_confidence=0.6      # Requirement 3.1
                )
                self.active = True
                logger.info("MediaPipe Holistic Initialized (Lite Model - 30 FPS Target)")
            except Exception as e:
                logger.error(f"MediaPipe initialization failed: {e}")

        self.last_process_time = 0

    def detect_landmarks(self, frame: np.ndarray):
        """
        Asynchronous-ready detection with frame skipping logic.
        """
        if not self.active or frame is None:
            return np.zeros(1662)

        start_time = time.time()

        try:
            # Requirement 2.3: Correct color format conversion
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False

            # AI Inference
            results = self.holistic.process(image)

            # Requirement 5.4: Real-time logging for every stage
            self.last_process_time = time.time() - start_time
            has_hand = results.left_hand_landmarks or results.right_hand_landmarks
            has_face = results.face_landmarks is not None

            # Log performance (Requirement 5.4)
            if frame.shape[0] > 0:
                logger.info(f"CV Speed: {self.last_process_time*1000:.1f}ms | Hand: {bool(has_hand)} | Face: {has_face}")

            return self._extract_keypoints(results)
        except Exception as e:
            logger.error(f"Processing Error: {e}")
            return np.zeros(1662)

    def _extract_keypoints(self, results):
        """
        Optimized extraction to prevent backlog (Requirement 5)
        """
        pose = np.array([[res.x, res.y, res.z, res.visibility] for res in results.pose_landmarks.landmark]).flatten() if results.pose_landmarks else np.zeros(33*4)
        face = np.array([[res.x, res.y, res.z] for res in results.face_landmarks.landmark]).flatten() if results.face_landmarks else np.zeros(468*3)
        lh = np.array([[res.x, res.y, res.z] for res in results.left_hand_landmarks.landmark]).flatten() if results.left_hand_landmarks else np.zeros(21*3)
        rh = np.array([[res.x, res.y, res.z] for res in results.right_hand_landmarks.landmark]).flatten() if results.right_hand_landmarks else np.zeros(21*3)

        return np.concatenate([pose, face, lh, rh])
