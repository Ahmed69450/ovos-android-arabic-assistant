# test_weather_skill.py
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath("app/src/main/python"))
from ovos_android.bus import AndroidMessageBus
from ovos_android.message import Message
from ovos_android.skills.weather_skill import WeatherSkill

class TestWeatherSkill(unittest.TestCase):
    def setUp(self):
        self.bus = AndroidMessageBus()
        self.skill = WeatherSkill(self.bus)
        self.skill.initialize()
        self.spoken = []
        self.bus.on("speak", lambda msg: self.spoken.append(msg.data.get("utterance", "")))

    def test_fetch_weather_known_city(self):
        msg = Message("weather_skill", data={"utterance": "ما حالة الطقس في الرياض", "slots": {"location": "الرياض"}})
        self.skill.handle_weather(msg)
        self.assertTrue(len(self.spoken) > 0)
        resp = self.spoken[0]
        self.assertIn("الرياض", resp)
        self.assertTrue("درجة" in resp or "الطقس" in resp)
        self.assertNotIn("\n", resp)
        self.assertNotIn("\r", resp)

    def test_fetch_weather_default_city_when_empty(self):
        msg = Message("weather_skill", data={"utterance": "كيف الجو اليوم", "slots": {}})
        self.skill.handle_weather(msg)
        self.assertTrue(len(self.spoken) > 0)
        resp = self.spoken[0]
        self.assertTrue("الطقس" in resp or "درجة" in resp)

    def test_fallback_on_unrecognized_location(self):
        msg = Message("weather_skill", data={"utterance": "الطقس في مدينة_غير_موجودة_بتاتا", "slots": {"location": "مدينة_غير_موجودة_بتاتا"}})
        self.skill.handle_weather(msg)
        self.assertTrue(len(self.spoken) > 0)

if __name__ == "__main__":
    unittest.main()
