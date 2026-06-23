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

    def transcribe(self, audio_bytes: bytes, retries=1) -> tuple[str, str]:
        """
        Transcribes audio bytes to text. Returns (text, error_message).
        """
        temp_input_path = None
        temp_wav_path = None
        error_msg = "Unknown error"

        # Check for ffmpeg
        import shutil
        has_ffmpeg = shutil.which("ffmpeg") is not None

        for attempt in range(attempt_count := retries + 1):
            try:
                # 1. Save raw input to a temp file
                is_webm = audio_bytes.startswith(b'\x1a\x45\xdf\xa3')
                suffix = '.webm' if is_webm else '.raw'
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(audio_bytes)
                    temp_input_path = tmp.name

                if is_webm and not has_ffmpeg:
                    error_msg = "FFmpeg not found. Cannot process WebM audio from browser. Please install FFmpeg."
                    logger.error(error_msg)
                    return "", error_msg

                # 2. Convert to WAV
                if PYDUB_AVAILABLE:
                    try:
                        audio = AudioSegment.from_file(temp_input_path)
                        temp_wav_path = temp_input_path + ".wav"
                        audio.export(temp_wav_path, format="wav")
                        process_path = temp_wav_path
                    except Exception as e:
                        logger.warning(f"pydub conversion failed: {e}")
                        process_path = temp_input_path
                else:
                    process_path = temp_input_path

                # 3. Use SpeechRecognition
                with sr.AudioFile(process_path) as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.1)
                    audio_data = self.recognizer.record(source)

                # 4. Recognize
                response = self.recognizer.recognize_google(audio_data, show_all=True)

                if not response or 'alternative' not in response:
                    error_msg = "No speech recognized. Try speaking louder or check your mic."
                    continue

                best_guess = response['alternative'][0]
                text = best_guess.get('transcript', "")
                return text, ""

            except sr.UnknownValueError:
                error_msg = "Google Speech Recognition could not understand audio"
            except sr.RequestError as e:
                error_msg = f"Could not request results from Google Speech Recognition service; {e}"
            except Exception as e:
                error_msg = f"Transcription error: {str(e)}"
                logger.error(error_msg)
            finally:
                # Cleanup temp files
                for path in [temp_input_path, temp_wav_path]:
                    if path and os.path.exists(path):
                        try: os.remove(path)
                        except: pass
                temp_input_path = None
                temp_wav_path = None

        return "", error_msg
