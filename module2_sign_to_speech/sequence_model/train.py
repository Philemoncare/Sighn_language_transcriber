import os
import sys
import numpy as np
import json
import datetime
import logging
from types import ModuleType

# NumPy Compatibility Layer
if not hasattr(np, "complex_"): np.complex_ = np.complex128
if not hasattr(np, "float_"): np.float_ = np.float64
if not hasattr(np, "int_"): np.int_ = np.int64

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Input, Dropout, BatchNormalization, Bidirectional
    from tensorflow.keras.utils import to_categorical
    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
    TRAIN_TF_AVAILABLE = True
except ImportError:
    TRAIN_TF_AVAILABLE = False

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# Internal Imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from module2_sign_to_speech.sequence_model.data_collection import DataCollector

logger = logging.getLogger("Modern_Trainer")

def build_modern_architecture(input_shape, num_actions):
    """
    Architectural Improvement: Bidirectional LSTM with Batch Normalization
    Provides better temporal feature extraction for sign language.
    """
    model = Sequential([
        Input(shape=input_shape),
        # Spatial-Temporal Feature Extraction
        BatchNormalization(),
        Bidirectional(LSTM(128, return_sequences=True, activation='tanh')),
        Dropout(0.3),
        Bidirectional(LSTM(256, return_sequences=True, activation='tanh')),
        Dropout(0.3),
        Bidirectional(LSTM(128, return_sequences=False, activation='tanh')),
        BatchNormalization(),

        # Classification Head
        Dense(128, activation='relu'),
        Dropout(0.4),
        Dense(64, activation='relu'),
        Dense(num_actions, activation='softmax')
    ])
    return model

def train_model(actions=None, progress_callback=None, epochs=100, batch_size=32):
    if not TRAIN_TF_AVAILABLE:
        logger.error("TensorFlow not found. Training aborted.")
        return

    # 1. Prepare Actions & Metadata
    if actions is None:
        actions = ['hello', 'thanks', 'i_love_you', 'please', 'sorry']

    actions = sorted(list(set([a.strip() for a in actions])))
    num_actions = len(actions)

    # 2. Load Data
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_path = os.path.join(project_root, 'MP_Data')
    collector = DataCollector(data_path=data_path)

    logger.info(f"Loading data for: {actions}")
    X, y = collector.load_processed_data(actions)

    if X is None or len(X) == 0:
        logger.error("No training data found.")
        if progress_callback: progress_callback(-1)
        return

    # DATASET SAFETY: If we have very few samples, we must duplicate them (Augmentation)
    # to allow the train_test_split to function without crashing.
    if len(X) < 10:
        logger.warning(f"Extremely small dataset ({len(X)} samples). Applying emergency augmentation.")
        X_orig, y_orig = X.copy(), y.copy()
        # Ensure we have at least 15 samples total
        iterations = (15 // len(X)) + 1
        for _ in range(iterations):
            noise = np.random.normal(0, 0.002, X_orig.shape).astype(np.float32)
            X = np.concatenate([X, X_orig + noise], axis=0)
            y = np.concatenate([y, y_orig], axis=0)

    # CLASS SAFETY: If only 1 action is provided, we MUST add a "background" class.
    if num_actions == 1:
        logger.info(f"Only 1 action '{actions[0]}' detected. Adding synthetic 'nothing' class for stability.")
        bg_data = np.random.normal(0, 0.01, (len(X), 30, 1662)).astype(np.float32)
        X = np.concatenate([X, bg_data], axis=0)
        y = np.concatenate([y, np.ones(len(y), dtype=int) * 1], axis=0)
        actions.append("nothing")
        num_actions = 2

    y_cat = to_categorical(y, num_classes=num_actions)

    # Adjust test_size for small datasets to ensure at least 1 sample in each set
    actual_test_size = 0.2 if len(X) > 20 else 1 / len(X)
    X_train, X_test, y_train, y_test = train_test_split(X, y_cat, test_size=actual_test_size, random_state=42)

    # 3. Build & Compile
    model = build_modern_architecture((30, 1662), num_actions)
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['categorical_accuracy'])

    # 4. Modern Training Callbacks
    callbacks = [
        EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=0.00001),
        ModelCheckpoint('best_model.h5', monitor='val_categorical_accuracy', save_best_only=True)
    ]

    # 5. Execute Training
    logger.info("Starting modern training pipeline...")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=callbacks,
        verbose=1
    )

    # 6. Save Model & Mandatory Metadata (Ensures no "faking" symbols)
    model.save(os.path.join(project_root, 'action_recognition.h5'))

    metadata = {
        "trained_at": datetime.datetime.now().isoformat(),
        "actions": actions,
        "input_shape": [30, 1662],
        "accuracy": float(history.history['categorical_accuracy'][-1])
    }

    metadata_path = os.path.join(project_root, 'model_metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=4)

    logger.info("Modern Training Complete. Metadata synced.")
    if progress_callback: progress_callback(100)

if __name__ == "__main__":
    train_model()
