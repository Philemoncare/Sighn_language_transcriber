import numpy as np

# COMPATIBILITY HACK: Fix NumPy 2.0 breaking changes for older TensorFlow
if not hasattr(np, "complex_"): np.complex_ = getattr(np, "complex128", None)
if not hasattr(np, "float_"): np.float_ = getattr(np, "float64", None)
if not hasattr(np, "int_"): np.int_ = getattr(np, "int64", None)
if not hasattr(np, "string_"): np.string_ = getattr(np, "bytes_", None)
if not hasattr(np, "unicode_"): np.unicode_ = getattr(np, "str_", None)

import tensorflow as tf

def convert_to_tflite(model_path, export_path):
    model = tf.keras.models.load_model(model_path)
    converter = tf.lite.TFLiteConverter.from_keras_model(model)

    # Optimization: Quantization
    converter.optimizations = [tf.lite.Optimize.DEFAULT]

    tflite_model = converter.convert()

    with open(export_path, 'wb') as f:
        f.write(tflite_model)
    print(f"Model optimized and exported to {export_path}")

if __name__ == "__main__":
    convert_to_tflite('action_recognition.h5', 'action_recognition_optimized.tflite')
