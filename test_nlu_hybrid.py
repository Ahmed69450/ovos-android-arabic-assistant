# test_nlu_hybrid.py
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath("app/src/main/python"))
from ovos_android.nlu_engine import ArabicNLUEngine
from ovos_android.dialogue_fsm import DialogueFSM

class TestHybridNLUEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        weights_path = os.path.abspath("app/src/main/assets/model_weights.json")
        intents_path = os.path.abspath("app/src/main/assets/intents.json")
        cls.engine = ArabicNLUEngine(weights_source=weights_path, intents_data_path=intents_path)

    def test_fuzzy_intent_with_typo_weather(self):
        # Typo: "الطقث" instead of "الطقس"
        result = self.engine.parse_intent("كيف الطقث في الرياض اليوم")
        self.assertEqual(result["intent"], "weather_skill")
        self.assertGreaterEqual(result["confidence"], 0.60)

    def test_fuzzy_intent_greeting_typo(self):
        # Typo: "مرجبا" instead of "مرحبا"
        result = self.engine.parse_intent("مرجبا يا صديقي")
        self.assertEqual(result["intent"], "greeting_skill")
        self.assertGreaterEqual(result["confidence"], 0.60)

    def test_fuzzy_stop_command(self):
        # Typo: "توغف" instead of "توقف"
        result = self.engine.parse_intent("توغف عن الكلام")
        self.assertEqual(result["intent"], "stop_skill")
        self.assertGreaterEqual(result["confidence"], 0.70)

    def test_followup_context_intent(self):
        fsm = DialogueFSM()
        ctx = fsm.update_turn(intent="weather_skill", slots={"location": "الرياض"})
        # Short followup query
        result = self.engine.parse_intent("وغداً؟", context=ctx)
        self.assertEqual(result["intent"], "weather_skill")

if __name__ == "__main__":
    unittest.main()
