# test_dialogue_fsm.py
import unittest
import sys
import os
import time

sys.path.insert(0, os.path.abspath("app/src/main/python"))
from ovos_android.dialogue_fsm import DialogueFSM, DialogueState

class TestDialogueFSM(unittest.TestCase):
    def setUp(self):
        self.fsm = DialogueFSM(session_timeout_seconds=1.5)

    def test_initial_state(self):
        ctx = self.fsm.get_context()
        self.assertEqual(ctx.state, DialogueState.IDLE)
        self.assertEqual(ctx.last_intent, "")
        self.assertEqual(ctx.slots, {})

    def test_single_turn(self):
        ctx = self.fsm.update_turn(intent="weather_skill", slots={"location": "الرياض", "date": "اليوم"})
        self.assertEqual(ctx.state, DialogueState.ACTIVE_SESSION)
        self.assertEqual(ctx.last_intent, "weather_skill")
        self.assertEqual(ctx.slots["location"], "الرياض")
        self.assertEqual(ctx.slots["date"], "اليوم")

    def test_multi_turn_followup_preserves_slots(self):
        self.fsm.update_turn(intent="weather_skill", slots={"location": "الرياض", "date": "اليوم"})
        # Follow-up: User mentions date only ("وغداً")
        ctx = self.fsm.update_turn(intent="weather_skill", slots={"date": "غداً"})
        # Location from previous turn must be preserved
        self.assertEqual(ctx.slots["location"], "الرياض")
        self.assertEqual(ctx.slots["date"], "غداً")

    def test_awaiting_slot_state(self):
        ctx = self.fsm.update_turn(intent="weather_skill", slots={}, awaiting_slot="location")
        self.assertEqual(ctx.state, DialogueState.AWAITING_SLOT)
        self.assertEqual(ctx.awaiting_slot, "location")

    def test_session_timeout(self):
        self.fsm.update_turn(intent="weather_skill", slots={"location": "الرياض"})
        time.sleep(1.6)
        # Timeout expired, should reset to IDLE
        ctx = self.fsm.get_context()
        self.assertEqual(ctx.state, DialogueState.IDLE)
        self.assertEqual(ctx.slots, {})

    def test_explicit_reset(self):
        self.fsm.update_turn(intent="weather_skill", slots={"location": "دبي"})
        self.fsm.reset()
        ctx = self.fsm.get_context()
        self.assertEqual(ctx.state, DialogueState.IDLE)
        self.assertEqual(ctx.slots, {})

if __name__ == "__main__":
    unittest.main()
