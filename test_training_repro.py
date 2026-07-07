import os
import numpy as np

try:
    import tensorflow as tf
    print(f"TF Version: {tf.__version__}")
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Input, Bidirectional, BatchNormalization, Dropout

    def build_model():
        model = Sequential([
            Input(shape=(30, 1662)),
            BatchNormalization(),
            Bidirectional(LSTM(64, return_sequences=True, activation='tanh')),
            Bidirectional(LSTM(64, return_sequences=False, activation='tanh')),
            Dense(64, activation='relu'),
            Dense(2, activation='softmax')
        ])
        return model

    print("Building model...")
    model = build_model()
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])

    print("Creating dummy data...")
    X = np.random.normal(0, 1, (10, 30, 1662)).astype(np.float32)
    y = np.array([0, 1, 0, 1, 0, 1, 0, 1, 0, 1])

    print("Starting fit...")
    model.fit(X, y, epochs=1, verbose=1)
    print("Fit SUCCESS")

except Exception as e:
    print(f"Fit FAILED: {e}")
    import traceback
    traceback.print_exc()
