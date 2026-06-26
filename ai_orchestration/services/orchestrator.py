import logging
import asyncio
import numpy as np

from typing import Optional, List, Dict
from sqlalchemy.orm import Session

# Import Engines
from module1_speech_to_sign.speech_recognition.engine import SpeechRecognitionEngine
from module1_speech_to_sign.nlp_engine.nlp_processor import NLPEngine
from module1_speech_to_sign.sign_translation.translator import SignTranslationEngine
from module1_speech_to_sign.avatar_renderer.renderer import AvatarRenderer

from module2_sign_to_speech.cv_module.landmark_detection import CVModule
from module2_sign_to_speech.sequence_model.recognizer import SequenceModel
from module2_sign_to_speech.tts_engine.engine import TTSEngine

# Import Pipelines
from module1_speech_to_sign.pipeline import SpeechToSignPipeline
from module2_sign_to_speech.pipeline import SignToSpeechPipeline
from ai_orchestration.services.training_pipeline import TrainingPipeline

from database_layer.db_manager import GestureLibraryModel

logger = logging.getLogger("AI_Orchestrator")

class AIOrchestrator:
    """
    AI PREDICTION & ORCHESTRATION LAYER
    Architecture: Coordinates Module 1 / Module 2 pipelines · model inference scheduling
    · conversation context · multi-language routing
    """
    def __init__(self):
        # Initialize Core Engines
        self.speech_engine = SpeechRecognitionEngine()
        self.nlp_engine = NLPEngine()
        self.sign_translator = SignTranslationEngine()
        self.avatar_renderer = AvatarRenderer()
        self.cv_module = CVModule()
        self.seq_model = SequenceModel(actions=None)
        self.tts_engine = TTSEngine()

        # Initialize Architecture Pipelines
        self.m1_pipeline = SpeechToSignPipeline(
            self.speech_engine, self.nlp_engine, self.sign_translator, self.avatar_renderer
        )
        self.m2_pipeline = SignToSpeechPipeline(
            self.cv_module, self.seq_model, self.tts_engine
        )
        self.training_pipeline = TrainingPipeline(self)

    def sync_vocabulary(self, db: Session):
        try:
            gestures = db.query(GestureLibraryModel).all()
            if gestures:
                # ALIGNMENT FIX: Sort actions alphabetically to match training pipeline logic
                actions = sorted([g.gesture_name for g in gestures])

                # Handle the single-action "background" case introduced during training
                if len(actions) == 1:
                    actions.append("background")
                    logger.info("Orchestration: Single gesture detected, adding 'background' for model alignment.")

                self.seq_model.actions = np.array(actions)
                self.sign_translator.sync_from_gesture_library(gestures)
                logger.info(f"Orchestration: Sync complete ({len(actions)} actions, sorted)")
            return gestures
        except Exception as e:
            logger.error(f"Vocabulary sync failed: {e}")
            return []

    def reload_model(self, model_path: str, actions: Optional[List[str]] = None):
        """Reloads the underlying sequence recognition model"""
        try:
            if not actions:
                actions = self.seq_model.actions.tolist() if hasattr(self.seq_model.actions, "tolist") else list(self.seq_model.actions)
            self.seq_model.reload_model(model_path, actions)
            logger.info(f"Orchestration: Model reloaded from {model_path}")
            return True
        except Exception as e:
            logger.error(f"Model reload failed: {e}")
            return False

    async def speech_to_sign(self, audio_data: bytes, language: str = "English") -> Dict:
        """Executes Module 1 Pipeline"""
        return await self.m1_pipeline.execute(audio_data, language)

    async def sign_to_speech(self, landmarks_sequence: List, language: str = "English") -> Dict:
        """Executes Module 2 Pipeline"""
        return await self.m2_pipeline.execute(landmarks_sequence, language)

# Singleton Instance
orchestrator = AIOrchestrator()
