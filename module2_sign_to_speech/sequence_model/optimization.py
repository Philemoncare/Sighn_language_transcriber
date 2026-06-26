import os
import numpy as np

# COMPATIBILITY HACK: Fix NumPy 2.0 breaking changes for older TensorFlow
if not hasattr(np, "complex_"): np.complex_ = getattr(np, "complex128", None)
if not hasattr(np, "float_"): np.float_ = getattr(np, "float64", None)
if not hasattr(np, "int_"): np.int_ = getattr(np, "int64", None)
if not hasattr(np, "string_"): np.string_ = getattr(np, "bytes_", None)
if not hasattr(np, "unicode_"): np.unicode_ = getattr(np, "str_", None)

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from module2_sign_to_speech.sequence_model.data_collection import DataCollector

def build_tunable_model(hp_layers, hp_units, hp_dropout, input_shape, no_actions):
    model = Sequential()
    for i in range(hp_layers):
        model.add(LSTM(hp_units, return_sequences=(i < hp_layers - 1), activation='relu', input_shape=input_shape if i == 0 else None))
        model.add(Dropout(hp_dropout))

    model.add(Dense(hp_units // 2, activation='relu'))
    model.add(Dense(no_actions, activation='softmax'))
    return model

def run_grid_search():
    actions = np.array(['hello', 'thanks', 'i_love_you', 'please', 'sorry'])
    collector = DataCollector()
    X, y = collector.load_processed_data(actions)

    # Hyperparameter ranges
    layers_options = [2, 3]
    units_options = [64, 128]
    dropout_options = [0.2, 0.3]

    best_acc = 0
    best_config = {}

    for layers in layers_options:
        for units in units_options:
            for dropout in dropout_options:
                print(f"Testing Config: Layers={layers}, Units={units}, Dropout={dropout}")
                model = build_tunable_model(layers, units, dropout, (30, 1662), len(actions))
                model.compile(optimizer='Adam', loss='categorical_crossentropy', metrics=['accuracy'])

                # Short training for quick evaluation
                history = model.fit(X, tf.keras.utils.to_categorical(y), epochs=10, batch_size=32, verbose=0, validation_split=0.2)
                val_acc = max(history.history['val_accuracy'])

                if val_acc > best_acc:
                    best_acc = val_acc
                    best_config = {'layers': layers, 'units': units, 'dropout': dropout}

    print(f"Best Configuration: {best_config} with Accuracy: {best_acc}")

if __name__ == "__main__":
    run_grid_search()
