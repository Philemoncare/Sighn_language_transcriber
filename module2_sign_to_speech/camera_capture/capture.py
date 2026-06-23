import cv2
import threading
import queue
import time
import logging

logger = logging.getLogger("Camera_Capture")

class CameraCapture:
    """
    PERFORMANCE FIX: Separate thread for camera capture (Requirement 5.1)
    to prevent frame backlog and lag.
    """
    def __init__(self, source=0):
        self.cap = cv2.VideoCapture(source)
        # Requirement 2.1: Initialization and continuous read
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.q = queue.Queue(maxsize=3) # Small buffer to prevent lag (Requirement 5.2)
        self.stopped = False

        if not self.cap.isOpened():
            logger.error("Could not open video source")
            return

        # Start capture thread
        self.t = threading.Thread(target=self._reader)
        self.t.daemon = True
        self.t.start()
        logger.info("Threaded Camera Capture Started @ 30 FPS")

    def _reader(self):
        while not self.stopped:
            ret, frame = self.cap.read()
            if not ret:
                break
            if not self.q.empty():
                try:
                    self.q.get_nowait() # Discard old frame (Requirement 5.2 - Skip Strategy)
                except queue.Empty:
                    pass
            self.q.put(frame)
        self.cap.release()

    def get_frame(self):
        """
        Non-blocking frame retrieval.
        """
        try:
            return self.q.get(timeout=0.1)
        except queue.Empty:
            return None

    def release(self):
        self.stopped = True
        if self.t.is_alive():
            self.t.join()
