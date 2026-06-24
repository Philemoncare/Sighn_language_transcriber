import logging
import asyncio
import numpy as np
from typing import Optional, List, Dict
from sqlalchemy.orm import Session

# Import Domain Modules
from module1_speech_to_sign.speech_recognition.engine import SpeechRecognitionEngine
from module1_speech_to_sign.nlp_engine.nlp_processor import NLPEngine
from module1_speech_to_sign.sign_translation.translator import SignTranslationEngine
from module1_speech_to_sign.avatar_renderer.renderer import AvatarRenderer

from module2_sign_to_speech.cv_module.landmark_detection import CVModule
from module2_sign_to_speech.sequence_model.recognizer import SequenceModel
from module2_sign_to_speech.tts_engine.engine import TTSEngine

from database_layer.db_manager import GestureLibraryModel, ConversationModel

logger = logging.getLogger("SnLag_Orchestrator")

class AIOrchestrator:
    """
    Coordinates all AI modules and manages execution flow.
    Ensures isolation of components and handles fallback mechanisms.
    """
    def __init__(self):
        # Module 1 Pipeline
        self.speech_engine = SpeechRecognitionEngine()
        self.nlp_engine = NLPEngine()
        self.sign_translator = SignTranslationEngine()
        self.avatar_renderer = AvatarRenderer()

        # Module 2 Pipeline
        self.cv_module = CVModule()
        self.seq_model = SequenceModel(actions=None)
        self.tts_engine = TTSEngine()

    def sync_vocabulary(self, db: Session):
        """Synchronizes the gesture library with the sequence model and translator"""
        try:
            gestures = db.query(GestureLibraryModel).all()
            if gestures:
                actions = np.array([g.gesture_name for g in gestures])
                self.seq_model.actions = actions
                self.sign_translator.sync_from_gesture_library(gestures)
                logger.info(f"Orchestration: Vocabulary synchronized with {len(gestures)} gestures.")
            return gestures
        except Exception as e:
            logger.error(f"Vocabulary sync failed: {e}")
            return []

    async def speech_to_sign(self, audio_data: bytes, language: str = "English") -> Dict:
        """
        Full pipeline: Audio -> Text -> NLP -> Sign Sequence -> Avatar Render
        """
        try:
            # 1. Speech Recognition
            text_result, error = await asyncio.to_thread(self.speech_engine.transcribe, audio_data, language=language)
            if error: return {"status": "error", "message": f"Speech error: {error}"}
            if not text_result: return {"status": "error", "message": "No speech detected"}

            # 2. NLP & Translation (using cache if possible - handled at API layer or here)
            analyzed = self.nlp_engine.analyze_text(text_result, source_lang=language)
            sequence = self.sign_translator.translate_to_sign_sequence(analyzed)

            # 3. Rendering
            render = self.avatar_renderer.render_sign_sequence(sequence)

            return {
                "status": "success",
                "original_text": text_result,
                "result": render
            }
        except Exception as e:
            logger.error(f"Speech-to-Sign Pipeline failure: {e}")
            return {"status": "error", "message": str(e)}

    async def sign_to_speech(self, landmarks_sequence: List, language: str = "English") -> Dict:
        """
        Full pipeline: Landmarks -> Sequence Model -> Text -> TTS
        """
        try:
            # 1. Prediction
            res = await asyncio.to_thread(self.seq_model.predict_with_confidence, landmarks_sequence)
            sign = res.get("sign")
            confidence = res.get("confidence", 0)

            if not sign or sign == "nothing" or confidence < 0.6:
                return {"status": "error", "message": "No clear sign detected"}

            # 2. TTS
            audio = self.tts_engine.synthesize(sign, language=language)

            return {
                "status": "success",
                "text": sign,
                "confidence": confidence,
                "audio": audio
            }
        except Exception as e:
            logger.error(f"Sign-to-Speech Pipeline failure: {e}")
            return {"status": "error", "message": str(e)}

# Singleton instance
orchestrator = AIOrchestrator()
