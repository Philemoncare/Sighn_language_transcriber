import os
import sys
import numpy as np

# COMPATIBILITY HACK: Fix NumPy/JAX friction for TensorFlow
from types import ModuleType
if not hasattr(np, "dtypes"):
    np.dtypes = ModuleType("dtypes")
if not hasattr(np.dtypes, "StringDType"):
    class MockStringDType:
        def __call__(self, *args, **kwargs): return np.str_
    np.dtypes.StringDType = MockStringDType()

import tensorflow as tf
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import sys
import json
import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from module2_sign_to_speech.sequence_model.recognizer import SequenceModel
from module2_sign_to_speech.sequence_model.data_collection import DataCollector

def train_model(actions=None, progress_callback=None, epochs=500, batch_size=32):
    if actions is None:
        actions = np.array(['hello', 'thanks', 'i_love_you', 'please', 'sorry'])
    else:
        actions = np.array(actions)

    if progress_callback: progress_callback(10)

    # Architecture: Ensure we use the project root for data consistency
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_path = os.path.join(project_root, 'MP_Data')

    print(f"PIPELINE: Initializing DataCollector with path: {data_path}")
    collector = DataCollector(data_path=data_path)

    # 1. Load and Validate Data
    print(f"PIPELINE: Loading data for actions: {actions}")
    try:
        X, y = collector.load_processed_data(actions)
    except Exception as le:
        print(f"PIPELINE ERROR: Failed to load data: {le}")
        if progress_callback: progress_callback(-1)
        return

    if X is None or X.size == 0:
        print(f"PIPELINE ERROR: No valid sequences found in {data_path} for actions {actions}")
        if progress_callback: progress_callback(-1)
        return

    # PERFORMANCE FIX: If only one action is provided, we create a "negative" class
    # to allow the classifier to have at least 2 categories (Binary Classification)
    if len(actions) == 1:
        print(f"Only one action detected: {actions[0]}. Creating 'background' class for stability.")
        # Create background data: random noise with similar scale
        X_bg = np.random.normal(0, 0.01, X.shape)
        X = np.concatenate([X, X_bg], axis=0)
        y = np.concatenate([y, np.ones(y.shape) * 1], axis=0) # Index 1 for background
        actions = np.array([actions[0], "background"])

    if progress_callback: progress_callback(30)
    # Data Augmentation: Adding slight noise to landmarks to improve robustness
    noise = np.random.normal(0, 0.001, X.shape)
    X_augmented = np.concatenate([X, X + noise], axis=0)
    y_augmented = np.concatenate([y, y], axis=0)

    y_cat = to_categorical(y_augmented).astype(int)

    # Robust Split: Ensure we have enough samples for stratification
    try:
        X_train, X_test, y_train, y_test = train_test_split(X_augmented, y_cat, test_size=0.1, stratify=y_augmented)
    except ValueError:
        print("PIPELINE WARNING: Stratified split failed (too few samples). Falling back to random split.")
        X_train, X_test, y_train, y_test = train_test_split(X_augmented, y_cat, test_size=0.1)

    # 2. Initialize Model
    seq_manager = SequenceModel(actions=actions)
    model = seq_manager.model

    model.compile(optimizer='Adam', loss='categorical_crossentropy', metrics=['categorical_accuracy'])

    if progress_callback: progress_callback(40)

    # 3. Callbacks for Optimization
    class ProgressLogger(tf.keras.callbacks.Callback):
        def on_epoch_end(self, epoch, logs=None):
            if progress_callback:
                # Map epochs to 30% - 90% progress range
                prog = 30 + int(((epoch + 1) / epochs) * 60)
                progress_callback(prog)

    # Define callbacks
    early_stopping = EarlyStopping(monitor='categorical_accuracy', min_delta=0.001, patience=50, verbose=1, mode='max', restore_best_weights=True)
    checkpoint = ModelCheckpoint('action_recognition.h5', monitor='categorical_accuracy', verbose=1, save_best_only=True, mode='max')
    best_checkpoint = ModelCheckpoint('best_model.h5', monitor='val_categorical_accuracy', verbose=1, save_best_only=True, mode='max')

    callbacks = [early_stopping, checkpoint, best_checkpoint, ProgressLogger()]

    # 4. Training
    print("Starting Model Training...")
    history = model.fit(
        X_train, y_train,
        epochs=epochs,
        batch_size=batch_size,
        callbacks=callbacks,
        validation_data=(X_test, y_test),
        verbose=1
    )

    if progress_callback: progress_callback(95)
    # 5. Full Performance Evaluation
    print("Evaluating Model...")
    yhat = model.predict(X_test)
    ytrue = np.argmax(y_test, axis=1)
    yhat = np.argmax(yhat, axis=1)

    report = classification_report(ytrue, yhat, target_names=actions, output_dict=True)
    conf_matrix = confusion_matrix(ytrue, yhat).tolist()

    accuracy = accuracy_score(ytrue, yhat)
    print(f"Final Test Accuracy: {accuracy}")

    model_version = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    # Save Performance Report
    report_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "model_version": model_version,
        "actions": actions.tolist(),
        "accuracy": accuracy,
        "classification_report": report,
        "confusion_matrix": conf_matrix,
        "training_history": {
            "loss": history.history['loss'],
            "accuracy": history.history['categorical_accuracy'],
            "val_loss": history.history['val_loss'],
            "val_accuracy": history.history['val_categorical_accuracy']
        }
    }

    os.makedirs('models', exist_ok=True)
    with open(f'models/report_{model_version}.json', 'w') as f:
        json.dump(report_data, f, indent=4)

    with open('latest_report.json', 'w') as f:
        json.dump(report_data, f, indent=4)

    # 6. Save Final Production Model
    model.save('action_recognition.h5')
    print("Training Pipeline Complete. Model and Report Saved.")

if __name__ == "__main__":
    train_model()
