import speech_recognition as sr
import io
import tempfile
import os
import logging
import time
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

# Configure logging for the engine
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SpeechEngine")

class SpeechRecognitionEngine:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        # Set thresholds for better voice detection
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        logger.info("Modern Speech Recognition Engine Initialized with Noise Reduction capability")

    def transcribe(self, audio_bytes: bytes, language: str = "en-US", retries=1) -> tuple[str, str]:
        """
        Transcribes audio bytes to text using in-memory processing where possible.
        """
        error_msg = "Unknown error"

        # Map UI language names to Google Speech codes
        lang_map = {
            "English": "en-US",
            "French": "fr-FR",
            "Portuguese": "pt-PT",
            "Spanish": "es-ES",
            "GSL": "en-GH", # Ghana Sign Language often uses English context
            "Twi": "ak-GH",  # Akan/Twi
            "Ewe": "ee-GH",
            "Ga": "gaa-GH"
        }
        target_lang = lang_map.get(language, language)

        # Check for ffmpeg
        import shutil
        import os
        ffmpeg_path = shutil.which("ffmpeg")

        # Fallback for common Windows installation paths if not in PATH
        if not ffmpeg_path and os.name == 'nt':
            winget_base = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft/WinGet/Packages')
            if os.path.exists(winget_base):
                # Search for any Gyan.FFmpeg installation
                for folder in os.listdir(winget_base):
                    if folder.startswith("Gyan.FFmpeg"):
                        # Look for ffmpeg.exe in the bin folder within that package
                        search_dir = os.path.join(winget_base, folder)
                        for root, dirs, files in os.walk(search_dir):
                            if "ffmpeg.exe" in files:
                                ffmpeg_path = os.path.join(root, "ffmpeg.exe")
                                break
                    if ffmpeg_path: break

            if ffmpeg_path:
                # Add to path for pydub to find it
                bin_dir = os.path.dirname(ffmpeg_path)
                if bin_dir not in os.environ["PATH"]:
                    os.environ["PATH"] += os.pathsep + bin_dir

        for attempt in range(retries + 1):
            try:
                # Use BytesIO for in-memory processing
                audio_stream = io.BytesIO(audio_bytes)

                if audio_bytes.startswith(b'\x1a\x45\xdf\xa3'): # WebM
                    if not ffmpeg_path:
                        return "", "FFmpeg required for WebM processing."

                    if PYDUB_AVAILABLE:
                        audio = AudioSegment.from_file(audio_stream, format="webm")
                        wav_io = io.BytesIO()
                        audio.export(wav_io, format="wav")
                        wav_io.seek(0)
                        process_source = wav_io
                    else:
                        return "", "pydub required for WebM conversion."
                else:
                    process_source = audio_stream

                # SpeechRecognition
                with sr.AudioFile(process_source) as source:
                    # Faster noise adjustment for real-time feel
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.05)
                    audio_data = self.recognizer.record(source)

                response = self.recognizer.recognize_google(audio_data, language=target_lang, show_all=True)

                if not response or 'alternative' not in response:
                    error_msg = "No speech recognized."
                    continue

                return response['alternative'][0].get('transcript', ""), ""

            except sr.UnknownValueError:
                error_msg = "Google Speech Recognition could not understand audio"
            except sr.RequestError as e:
                error_msg = f"Could not request results from Google Speech Recognition service; {e}"
            except Exception as e:
                error_msg = f"Transcription error: {str(e)}"
                logger.error(error_msg)

        return "", error_msg
