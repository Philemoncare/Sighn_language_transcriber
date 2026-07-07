import os
import sys
import numpy as np
import collections
import json

try:
    import tensorflow as tf
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False

class SequenceModel:
    def __init__(self, model_path=None, actions=None):
        # Default Fallback
        self.actions = np.array(['nothing'])
        self.input_shape = (30, 1662)
        self.prediction_history = collections.deque(maxlen=5)
        self.model = None

        if TENSORFLOW_AVAILABLE:
            self._load_system(model_path, actions)
        else:
            print("CRITICAL: TensorFlow missing. AI Inference Disabled.")

    def _load_system(self, model_path=None, actions=None):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # 1. Try to find the latest model metadata
        metadata_path = os.path.join(project_root, 'model_metadata.json')
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r') as f:
                    meta = json.load(f)
                    self.actions = np.array(meta.get("actions", self.actions))
                    print(f"SequenceModel: Actions aligned from metadata: {self.actions}")
            except Exception as e:
                print(f"Metadata load error: {e}")

        # Override with manual actions if provided (e.g., from DB sync)
        if actions is not None:
            self.actions = np.array(actions)

        # 2. Load the H5 Model
        possible_paths = [
            model_path,
            os.path.join(project_root, 'best_model.h5'),
            os.path.join(project_root, 'action_recognition.h5')
        ]

        for path in possible_paths:
            if path and os.path.exists(path):
                try:
                    # Robust loading for different TF/Keras versions (Requirement 9)
                    # We try multiple import strategies to handle various environments
                    try:
                        # Strategy 1: Standard TF 2.x
                        self.model = tf.keras.models.load_model(path)
                    except (AttributeError, ImportError):
                        try:
                            # Strategy 2: Explicit Keras package
                            import keras
                            self.model = keras.models.load_model(path)
                        except:
                            # Strategy 3: Legacy TF
                            from tensorflow import keras as tf_keras
                            self.model = tf_keras.models.load_model(path)

                    print(f"SequenceModel: Model loaded successfully from {path}")
                    break
                except Exception as e:
                    print(f"Failed to load model at {path}: {e}")

    def reload_model(self, model_path, actions):
        """Standard reload for the orchestration layer."""
        if TENSORFLOW_AVAILABLE:
            self._load_system(model_path, actions)
            self.prediction_history.clear()

    def predict_with_confidence(self, sequence: list) -> dict:
        """
        Pure AI Inference. No mock data.
        If model is missing or sequence is low quality, returns 'nothing'.
        """
        if not TENSORFLOW_AVAILABLE or self.model is None or len(sequence) < 30:
            return {"sign": "nothing", "confidence": 0.0}

        try:
            frames = np.array(sequence[-30:]).astype(np.float32)

            # Movement & Quality Check
            # Ensure there is actual data in the hand landmarks (indices 1536+)
            if np.all(frames[:, 1536:] == 0) or np.var(frames) < 1e-7:
                return {"sign": "nothing", "confidence": 0.0}

            input_data = np.expand_dims(frames, axis=0)
            res_tensor = self.model(input_data, training=False)
            res = res_tensor.numpy()[0]

            predicted_idx = np.argmax(res)
            confidence = float(res[predicted_idx])

            # Label Safety Check
            if predicted_idx >= len(self.actions):
                return {"sign": "unknown_index", "confidence": 0.0}

            raw_sign = self.actions[predicted_idx]

            # Temporal Smoothing
            self.prediction_history.append(raw_sign)
            most_common, count = collections.Counter(self.prediction_history).most_common(1)[0]

            # Only switch sign if we have some consensus in the window
            final_sign = most_common if count >= 3 else "nothing"

            return {
                "sign": final_sign,
                "confidence": confidence if final_sign == raw_sign else confidence * 0.3
            }
        except Exception as e:
            print(f"Inference Error: {e}")
            return {"sign": "nothing", "confidence": 0.0}

    def predict_sign(self, sequence: list) -> str:
        res = self.predict_with_confidence(sequence)
        return res.get("sign", "nothing")
