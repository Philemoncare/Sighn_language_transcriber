import spacy
import logging

logger = logging.getLogger("NLPEngine")

class NLPEngine:
    def __init__(self, model="en_core_web_sm"):
        try:
            self.nlp = spacy.load(model)
        except:
            # Fallback if model not downloaded
            print(f"Warning: spaCy model {model} not found. Using blank model.")
            self.nlp = spacy.blank("en")

        # Local Ghanaian Language Mapping (Expansion for Universal Support)
        self.gh_mapping = {
            "ete sen": "how are you",
            "eye": "i am fine",
            "medaase": "thank you",
            "akwaaba": "welcome",
            "paa": "very much",
            "mo": "well done",
            "bra": "come",
            "ko": "go",
            "didi": "eat",
            "nom": "drink",
            "da": "sleep",
            "nyame": "god"
        }

        # Universal Language Intent Keywords
        self.intent_keywords = {
            "question": ["how", "what", "where", "why", "who", "comment", "qu'est-ce", "que", "como", "onde", "por que"],
            "request": ["want", "need", "get", "veux", "besoin", "quiero", "necesito", "preciso", "quero"]
        }

        print(f"Universal NLP Engine ({model}) Initialized")

    def _translate_gh_to_en(self, text: str) -> str:
        """Simple mapping for Ghanaian local languages (Twi/Ga/Ewe)"""
        text_lower = text.lower()
        for gh_word, en_word in self.gh_mapping.items():
            if gh_word in text_lower:
                text_lower = text_lower.replace(gh_word, en_word)
        return text_lower

    def analyze_text(self, text: str, source_lang: str = "English") -> dict:
        if not text:
            return {"original_text": "", "tokens": [], "entities": [], "intent": "none"}

        # Step 1: Handle Ghanaian local languages first if specified or detected
        processed_text = self._translate_gh_to_en(text)

        # Step 2: In a production environment, we would use a Translation API here
        # for languages like French, Spanish, etc., translating to English for sign mapping.
        # For now, we assume the Sign Dictionary will handle common tokens or fingerspelling.

        doc = self.nlp(processed_text)

        # Step 3: Multilingual Intent Recognition
        intent = "statement"
        text_lower = processed_text.lower()

        if any(kw in text_lower for kw in self.intent_keywords["question"]):
            intent = "question"
        elif any(kw in text_lower for kw in self.intent_keywords["request"]):
            intent = "request"

        # Refine with POS tagging if it's English (our main model)
        if self.nlp.lang == "en":
            for token in doc:
                if token.dep_ == "ROOT":
                    if token.lemma_ in ["want", "need", "get"]:
                        intent = "request"

        return {
            "original_text": text,
            "translated_text": processed_text,
            "tokens": [token.text for token in doc if not token.is_punct],
            "lemmas": [token.lemma_ for token in doc if not token.is_punct],
            "entities": [(ent.text, ent.label_) for ent in doc.ents],
            "intent": intent,
            "source_lang": source_lang
        }
