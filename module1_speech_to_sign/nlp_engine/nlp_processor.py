import spacy

class NLPEngine:
    def __init__(self, model="en_core_web_sm"):
        try:
            self.nlp = spacy.load(model)
        except:
            # Fallback if model not downloaded
            print(f"Warning: spaCy model {model} not found. Using blank model.")
            self.nlp = spacy.blank("en")
        print(f"NLP Engine ({model}) Initialized")

    def analyze_text(self, text: str) -> dict:
        if not text:
            return {"original_text": "", "tokens": [], "entities": [], "intent": "none"}

        doc = self.nlp(text)

        # Basic intent recognition based on root verb
        intent = "statement"
        for token in doc:
            if token.dep_ == "ROOT":
                if token.lemma_ in ["want", "need", "get"]:
                    intent = "request"
                elif token.tag_ == "VBZ" and any(t.text.lower() in ["how", "what", "where", "why", "who"] for t in doc):
                    intent = "question"

        return {
            "original_text": text,
            "tokens": [token.text for token in doc if not token.is_punct],
            "lemmas": [token.lemma_ for token in doc if not token.is_punct],
            "entities": [(ent.text, ent.label_) for ent in doc.ents],
            "intent": intent
        }
