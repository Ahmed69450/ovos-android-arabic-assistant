# test_full_integrated_pipeline.py
import unittest
import sys
import os
import json

sys.path.insert(0, os.path.abspath("app/src/main/python"))
import ovos_bridge

class TestFullIntegratedPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        m_path = os.path.abspath("app/src/main/assets/model_weights.json")
        i_path = os.path.abspath("app/src/main/assets/intents.json")
        ovos_bridge.initialize(m_path, i_path)

    def test_pipeline_turn1_and_turn2_context(self):
        # Turn 1: Weather query with location
        r1_str = ovos_bridge.process_utterance("ما هو الطقس في الرياض اليوم")
        r1 = json.loads(r1_str)
        self.assertEqual(r1["intent"], "weather_skill")
        self.assertIn("الرياض", r1["response"])
        self.assertNotIn("\n", r1["response"])
        self.assertNotIn("\r", r1["response"])

        # Turn 2: Follow-up question without explicit location
        r2_str = ovos_bridge.process_utterance("وغداً؟")
        r2 = json.loads(r2_str)
        self.assertEqual(r2["intent"], "weather_skill")
        # Location from turn 1 should be retained in turn 2
        self.assertIn("الرياض", r2["response"])
        self.assertNotIn("\n", r2["response"])

    def test_sanitization_guarantee(self):
        # Test query that returns dataset response containing markdown/newlines
        r_str = ovos_bridge.process_utterance("أعطني نصائح للبقاء بصحة جيدة")
        r = json.loads(r_str)
        self.assertNotIn("\n", r["response"])
        self.assertNotIn("\r", r["response"])
        self.assertNotIn("**", r["response"])
        self.assertNotIn("<p>", r["response"])

if __name__ == "__main__":
    unittest.main()
