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
