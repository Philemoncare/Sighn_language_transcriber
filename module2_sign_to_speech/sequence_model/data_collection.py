import os
import cv2
import numpy as np
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from module2_sign_to_speech.cv_module.landmark_detection import CVModule

class DataCollector:
    def __init__(self, data_path='MP_Data', no_sequences=30, sequence_length=30):
        self.data_path = data_path
        self.no_sequences = no_sequences
        self.sequence_length = sequence_length
        self.cv_module = CVModule()

    def create_folders(self, actions):
        for action in actions:
            for sequence in range(self.no_sequences):
                try:
                    os.makedirs(os.path.join(self.data_path, action, str(sequence)))
                except:
                    pass

    def collect_from_video(self, video_path, action_name, sequence_idx):
        cap = cv2.VideoCapture(video_path)
        for frame_num in range(self.sequence_length):
            ret, frame = cap.read()
            if not ret:
                break

            keypoints = self.cv_module.detect_landmarks(frame)
            npy_path = os.path.join(self.data_path, action_name, str(sequence_idx), str(frame_num))
            np.save(npy_path, keypoints)
        cap.release()

    def load_processed_data(self, actions):
        label_map = {label:num for num, label in enumerate(actions)}
        sequences, labels = [], []

        # Audit dataset
        missing_count = 0
        corrupted_count = 0

        for action in actions:
            action_path = os.path.join(self.data_path, action)
            if not os.path.exists(action_path):
                print(f"Warning: Directory for {action} missing.")
                continue

            for sequence in os.listdir(action_path):
                window = []
                valid_sequence = True

                for frame_num in range(self.sequence_length):
                    npy_file = os.path.join(self.data_path, action, str(sequence), "{}.npy".format(frame_num))

                    if not os.path.exists(npy_file):
                        missing_count += 1
                        valid_sequence = False
                        break

                    try:
                        res = np.load(npy_file)
                        if res.shape != (1662,): # Audit landmark shape
                            corrupted_count += 1
                            valid_sequence = False
                            break
                        window.append(res)
                    except Exception:
                        corrupted_count += 1
                        valid_sequence = False
                        break

                if valid_sequence and len(window) == self.sequence_length:
                    sequences.append(window)
                    labels.append(label_map[action])

        print(f"Dataset Audit Complete: {len(sequences)} valid sequences loaded.")
        if missing_count or corrupted_count:
            print(f"Validation found {missing_count} missing frames and {corrupted_count} corrupted files.")

        return np.array(sequences), np.array(labels)
