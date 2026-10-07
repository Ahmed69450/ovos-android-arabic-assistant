# test_knowledge_skills.py
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath("app/src/main/python"))
from ovos_android.bus import AndroidMessageBus
from ovos_android.message import Message
from ovos_android.skills.fallback_skill import FallbackSkill
from ovos_android.skills.knowledge_skills import GeneralKnowledgeSkill

class TestKnowledgeSkills(unittest.TestCase):
    def setUp(self):
        self.bus = AndroidMessageBus()
        self.spoken = []
        self.bus.on("speak", lambda msg: self.spoken.append(msg.data.get("utterance", "")))

    def test_fallback_with_local_qa(self):
        qa_pairs = [
            {"instruction": "ما هي عاصمة اليابان", "response": "عاصمة اليابان هي طوكيو."}
        ]
        skill = FallbackSkill(self.bus, qa_pairs=qa_pairs)
        skill.initialize()

        msg = Message("fallback_skill:handle_fallback", data={"utterance": "ما هي عاصمة اليابان"})
        skill.handle_fallback(msg)

        self.assertTrue(len(self.spoken) > 0)
        self.assertIn("طوكيو", self.spoken[0])
        self.assertNotIn("\n", self.spoken[0])

    def test_general_knowledge_skill_sanitization(self):
        qa_pairs = [
            {"instruction": "ما هي الذرة", "response": "**الذرة** هي أصغر جزء في العنصر.<br>تحتوي على نواة.\n\n"}
        ]
        skill = GeneralKnowledgeSkill(self.bus, qa_pairs=qa_pairs)
        skill.initialize()

        msg = Message("general_knowledge_skill", data={"utterance": "ما هي الذرة"})
        skill.handle_general(msg)

        self.assertTrue(len(self.spoken) > 0)
        resp = self.spoken[0]
        self.assertNotIn("**", resp)
        self.assertNotIn("<br>", resp)
        self.assertNotIn("\n", resp)

    def test_duckduckgo_query_online_or_fallback(self):
        skill = FallbackSkill(self.bus, qa_pairs=[])
        skill.initialize()

        msg = Message("fallback_skill:handle_fallback", data={"utterance": "من هو أينشتاين"})
        skill.handle_fallback(msg)

        self.assertTrue(len(self.spoken) > 0)
        resp = self.spoken[0]
        self.assertTrue(len(resp) > 5)
        self.assertNotIn("\n", resp)
        self.assertNotIn("\r", resp)

if __name__ == "__main__":
    unittest.main()
