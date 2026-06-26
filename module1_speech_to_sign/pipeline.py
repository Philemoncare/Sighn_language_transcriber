import logging
import asyncio
from typing import Dict

class SpeechToSignPipeline:
    """
    Architecture: Speech Recognition -> NLP Engine -> Sign Translation -> 3D Avatar Renderer
    Matches Module 1 of the System Architecture.
    """
    def __init__(self, speech_engine, nlp_engine, translator, renderer):
        self.speech_engine = speech_engine
        self.nlp_engine = nlp_engine
        self.translator = translator
        self.renderer = renderer
        self.logger = logging.getLogger("Module1_Pipeline")

    async def execute(self, audio_data: bytes, language: str = "English") -> Dict:
        try:
            # 1. Speech Recognition Engine
            text_result, error = await asyncio.to_thread(self.speech_engine.transcribe, audio_data, language=language)
            if error: return {"status": "error", "stage": "speech", "message": error}
            if not text_result: return {"status": "error", "stage": "speech", "message": "No speech detected"}

            # 2. NLP Processing Engine
            analyzed = self.nlp_engine.analyze_text(text_result, source_lang=language)

            # 3. Sign Translation Engine
            sequence = self.translator.translate_to_sign_sequence(analyzed)

            # 4. 3D Avatar Rendering Engine
            render = self.renderer.render_sign_sequence(sequence)

            return {
                "status": "success",
                "original_text": text_result,
                "result": render
            }
        except Exception as e:
            self.logger.error(f"Pipeline Execution Failed: {e}")
            return {"status": "error", "message": str(e)}
