import pyttsx3
import tempfile
import os

class TTSEngine:
    def __init__(self):
        self.engine = pyttsx3.init()
        print("Text-to-Speech Engine (pyttsx3) Initialized")

    def synthesize(self, text: str) -> bytes:
        if not text:
            return b""

        # pyttsx3 usually outputs to a file or speakers.
        # For a server-client model, we save to a temp file and read bytes.
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, "tts_output.wav")

        self.engine.save_to_file(text, temp_file)
        self.engine.runAndWait()

        with open(temp_file, "rb") as f:
            audio_data = f.read()

        os.remove(temp_file)
        return audio_data

    def speak(self, text: str):
        self.engine.say(text)
        self.engine.runAndWait()
