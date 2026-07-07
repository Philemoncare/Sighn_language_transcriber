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
from ai_orchestration.services.embedding_engine import embedding_engine

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
        res = await self.m2_pipeline.execute(landmarks_sequence, language)

        # Requirement 4 & 7: Contextual AI Embedding Assistance
        # If prediction confidence is low, search the vector database for the nearest validated neighbor.
        if res.get("status") == "success" and res.get("confidence", 0) < 0.90:
            logger.info(f"Orchestration: Low confidence ({res['confidence']}). Querying Vector Store...")

            # Use the mean landmark as a query vector (consistent with stage_embedding)
            query_vector = np.mean(landmarks_sequence, axis=0) if landmarks_sequence else np.zeros(1662)

            # Simple 768-dim truncation for initial FAISS implementation
            query_vector_768 = query_vector[:768].tolist()

            similar = embedding_engine.search(query_vector_768, k=1)
            if similar:
                match = similar[0]
                # If we find a very close match in the vector space, we can boost confidence or suggest correction
                logger.info(f"Orchestration: Vector match found for DS#{match['dataset_id']} (dist: {match['distance']})")

                # Logic: If distance is very small, it's likely the same sign
                if match['distance'] < 0.05: # Threshold for 'high similarity'
                     db = SessionLocal()
                     from database_layer.db_manager import SignDatasetModel
                     match_ds = db.query(SignDatasetModel).filter(SignDatasetModel.id == match['dataset_id']).first()
                     if match_ds and match_ds.label != res.get("sign"):
                         logger.info(f"Orchestration: Correcting '{res.get('sign')}' -> '{match_ds.label}' via Vector Hub.")
                         res["sign"] = match_ds.label
                         res["text"] = match_ds.label # Update for TTS
                         res["confidence"] = max(res["confidence"], 0.92) # Boost via semantic similarity
                     db.close()

        # Requirement 5: Enrich with Semantic Insights
        if res.get("status") == "success":
            sign = res.get("sign", "")
            res["meaning"] = f"Action: {sign.upper()}"
            # Detect if it's likely a single letter or word (Metadata)
            res["sign_type"] = "letter" if len(sign) == 1 else "word"

        return res

# Singleton Instance
orchestrator = AIOrchestrator()
