import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from module1_speech_to_sign.nlp_engine.nlp_processor import NLPEngine

def test_nlp_analysis():
    nlp = NLPEngine()
    result = nlp.analyze_text("How are you?")
    assert "intent" in result
    assert result["intent"] == "question"
    print("NLP Test Passed")

if __name__ == "__main__":
    test_nlp_analysis()
