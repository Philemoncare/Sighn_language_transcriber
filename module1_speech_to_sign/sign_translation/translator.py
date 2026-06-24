class SignTranslationEngine:
    def __init__(self):
        # Dictionary mapping words (various languages) to Sign Language Glosses and Symbol Descriptions
        # In a production system, this would be a massive DB or an AI-powered mapping
        self.sign_dictionary = {
            # English
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
            "sorry": {"gloss": "SORRY", "symbol": "😔", "description": "Closed fist circling on chest"},

            # French (Direct Mappings)
            "bonjour": {"gloss": "HELLO", "symbol": "👋", "description": "Salut / Bonjour"},
            "merci": {"gloss": "THANK-YOU", "symbol": "🙏", "description": "Merci"},
            "oui": {"gloss": "YES", "symbol": "✅", "description": "Nodding fist"},
            "non": {"gloss": "NO", "symbol": "❌", "description": "Index and middle fingers snapping to thumb"},

            # Spanish
            "hola": {"gloss": "HELLO", "symbol": "👋", "description": "Hola"},
            "gracias": {"gloss": "THANK-YOU", "symbol": "🙏", "description": "Gracias"},

            # Portuguese
            "obrigado": {"gloss": "THANK-YOU", "symbol": "🙏", "description": "Obrigado"},
            "bom": {"gloss": "GOOD", "symbol": "👍", "description": "Thumbs up"}
        }
        print("Universal Sign Translation Engine Initialized with Multilingual Core")

    def sync_from_gesture_library(self, gestures):
        """Extend the in-memory dictionary with gestures from the database."""
        for gesture in gestures:
            name = gesture.gesture_name.lower()
            if name not in self.sign_dictionary:
                self.sign_dictionary[name] = {
                    "gloss": name.upper().replace(" ", "-"),
                    "symbol": "🤟",
                    "description": gesture.description or f"Sign for {gesture.gesture_name}"
                }

    def translate_to_sign_sequence(self, analyzed_data: dict) -> list:
        # We can use lemmas from the NLP engine which might already be translated to English
        # or use the original tokens for direct multi-lingual mapping
        tokens = analyzed_data.get("tokens", [])
        lemmas = analyzed_data.get("lemmas", [])

        sign_sequence = []

        # Try lemmas first (often better for English), then tokens (for direct language match)
        for i in range(len(lemmas)):
            lemma_lower = lemmas[i].lower()
            token_lower = tokens[i].lower() if i < len(tokens) else lemma_lower

            if lemma_lower in self.sign_dictionary:
                sign_sequence.append(self.sign_dictionary[lemma_lower])
            elif token_lower in self.sign_dictionary:
                sign_sequence.append(self.sign_dictionary[token_lower])
            else:
                # Fingerspelling fallback
                for char in token_lower:
                    sign_sequence.append({
                        "gloss": f"LETTER-{char.upper()}",
                        "symbol": char.upper(),
                        "description": f"Hand shape for letter {char.upper()}"
                    })

        return sign_sequence
