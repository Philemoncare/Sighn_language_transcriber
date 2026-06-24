import pyttsx3
import tempfile
import os

class TTSEngine:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.voices = self.engine.getProperty('voices')
        print(f"Text-to-Speech Engine Initialized with {len(self.voices)} system voices")

    def _set_voice_by_lang(self, language: str):
        """Attempts to find a system voice that matches the requested language"""
        lang_lower = language.lower()
        # Common language code mappings for system voices
        search_terms = {
            "english": ["en", "english", "david", "zira"],
            "french": ["fr", "french", "hortense", "julie"],
            "spanish": ["es", "spanish", "helena", "pablo"],
            "portuguese": ["pt", "portuguese", "maria", "daniel"],
            "twi": ["en"], # Fallback to English for local languages if no specific voice
            "ewe": ["en"],
            "ga": ["en"]
        }

        terms = search_terms.get(lang_lower, ["en"])

        for voice in self.voices:
            for term in terms:
                if term in voice.name.lower() or term in voice.id.lower():
                    self.engine.setProperty('voice', voice.id)
                    return

        # Default to first voice if no match
        if self.voices:
            self.engine.setProperty('voice', self.voices[0].id)

    def synthesize(self, text: str, language: str = "English") -> bytes:
        if not text:
            return b""

        self._set_voice_by_lang(language)

        temp_dir = tempfile.gettempdir()
        # Use a unique filename to avoid collisions during concurrent requests
        import uuid
        temp_file = os.path.join(temp_dir, f"tts_{uuid.uuid4()}.wav")

        self.engine.save_to_file(text, temp_file)
        self.engine.runAndWait()

        audio_data = b""
        if os.path.exists(temp_file):
            with open(temp_file, "rb") as f:
                audio_data = f.read()
            os.remove(temp_file)

        return audio_data

    def speak(self, text: str):
        self.engine.say(text)
        self.engine.runAndWait()
