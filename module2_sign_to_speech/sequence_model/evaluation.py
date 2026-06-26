import numpy as np

# COMPATIBILITY HACK: Fix NumPy 2.0 breaking changes for older TensorFlow
if not hasattr(np, "complex_"): np.complex_ = getattr(np, "complex128", None)
if not hasattr(np, "float_"): np.float_ = getattr(np, "float64", None)
if not hasattr(np, "int_"): np.int_ = getattr(np, "int64", None)
if not hasattr(np, "string_"): np.string_ = getattr(np, "bytes_", None)
if not hasattr(np, "unicode_"): np.unicode_ = getattr(np, "str_", None)

from sklearn.metrics import multilabel_confusion_matrix, accuracy_score, classification_report
import tensorflow as tf
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from module2_sign_to_speech.sequence_model.data_collection import DataCollector

def evaluate_performance():
    actions = np.array(['hello', 'thanks', 'i_love_you', 'please', 'sorry'])
    model = tf.keras.models.load_model('action_recognition.h5')
    collector = DataCollector()

    X_test, y_test = collector.load_processed_data(actions) # In production use a separate test split

    yhat = model.predict(X_test)
    ytrue = np.argmax(y_test, axis=0) # This might need fix based on load_processed_data output
    # Fixed logic:
    ytrue = y_test
    yhat = np.argmax(yhat, axis=1)

    print("--- Classification Report ---")
    print(classification_report(ytrue, yhat, target_names=actions))

    print("--- Confusion Matrix ---")
    print(multilabel_confusion_matrix(ytrue, yhat))

    print(f"Overall Accuracy: {accuracy_score(ytrue, yhat)}")

if __name__ == "__main__":
    evaluate_performance()
