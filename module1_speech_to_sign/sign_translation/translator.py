class SignTranslationEngine:
    def __init__(self):
        # Dictionary mapping English words to Sign Language Glosses and Symbol Descriptions
        self.sign_dictionary = {
            "hello": {"gloss": "HELLO", "symbol": "👋", "description": "Open palm moving side to side"},
            "world": {"gloss": "WORLD", "symbol": "🌍", "description": "Both hands circling each other"},
            "thank": {"gloss": "THANK-YOU", "symbol": "🙏", "description": "Hand moves from chin forward"},
            "you": {"gloss": "YOU", "symbol": "☝️", "description": "Point index finger at person"},
            "i": {"gloss": "ME", "symbol": "👤", "description": "Point index finger at chest"},
            "want": {"gloss": "WANT", "symbol": "🤲", "description": "Both hands pulling towards body"},
            "help": {"gloss": "HELP", "symbol": "🆘", "description": "Closed fist on open palm moving up"},
            "name": {"gloss": "NAME", "symbol": "📛", "description": "Two fingers of each hand tapping"},
            "what": {"gloss": "WHAT", "symbol": "❓", "description": "Both palms up shaking slightly"},
            "where": {"gloss": "WHERE", "symbol": "📍", "description": "Index finger shaking side to side"},
            "please": {"gloss": "PLEASE", "symbol": "😊", "description": "Open palm circling on chest"},
            "sorry": {"gloss": "SORRY", "symbol": "😔", "description": "Closed fist circling on chest"}
        }
        print("Modern Sign Translation Engine Initialized with Symbols")

    def translate_to_sign_sequence(self, analyzed_data: dict) -> list:
        lemmas = analyzed_data.get("lemmas", [])
        sign_sequence = []

        for lemma in lemmas:
            lemma_lower = lemma.lower()
            if lemma_lower in self.sign_dictionary:
                sign_sequence.append(self.sign_dictionary[lemma_lower])
            else:
                # Fingerspelling fallback for unknown words
                for char in lemma_lower:
                    sign_sequence.append({
                        "gloss": f"LETTER-{char.upper()}",
                        "symbol": char.upper(),
                        "description": f"Hand shape for letter {char.upper()}"
                    })

        return sign_sequence
