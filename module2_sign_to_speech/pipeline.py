import logging
import asyncio
from typing import Dict, List

class SignToSpeechPipeline:
    """
    Architecture: Camera Capture -> Computer Vision Module -> Sequence Model -> TTS Engine
    Matches Module 2 of the System Architecture.
    """
    def __init__(self, cv_module, sequence_model, tts_engine):
        self.cv_module = cv_module # Optional if landmarks are provided
        self.sequence_model = sequence_model
        self.tts_engine = tts_engine
        self.logger = logging.getLogger("Module2_Pipeline")

    async def execute(self, landmarks_sequence: List, language: str = "English") -> Dict:
        try:
            # 1. Sequence Model (LSTM / Transformer)
            res = await asyncio.to_thread(self.sequence_model.predict_with_confidence, landmarks_sequence)
            sign = res.get("sign")
            confidence = res.get("confidence", 0)

            if not sign or sign == "nothing" or confidence < 0.5:
                return {"status": "error", "stage": "sequence", "message": "No clear sign detected"}

            self.logger.info(f"Pipeline: Detected '{sign}' with {confidence:.2f} confidence")

            # 2. Text-to-Speech Engine
            audio = self.tts_engine.synthesize(sign, language=language)

            return {
                "status": "success",
                "text": sign,
                "confidence": confidence,
                "audio": audio
            }
        except Exception as e:
            self.logger.error(f"Pipeline Execution Failed: {e}")
            return {"status": "error", "message": str(e)}
