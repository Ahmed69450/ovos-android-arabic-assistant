# -*- coding: utf-8 -*-
"""
مهارة الطقس والمناخ (WeatherSkill)
تقدم معلومات وتنبؤات الطقس المحلية باللغة العربية
"""

import random
from ..skill import OVOSSkill, intent_handler
from ..message import Message

class WeatherSkill(OVOSSkill):
    """مهارة الاستعلام عن حالة الطقس"""

    def __init__(self, bus):
        super().__init__("weather_skill", bus)
        self.weather_dialogs = [
            "الطقس اليوم معتدل ومناسب، وتتراوح درجات الحرارة حول معدلاتها الطبيعية.",
            "السماء صافية والرياح خفيفة، الأجواء ممتازة لممارسة الأنشطة اليومية.",
            "الجو لطيف اليوم مع بعض السحب المتفرقة، لا توجد مؤشرات لهطول أمطار قريبة."
        ]

    @intent_handler("weather_skill")
    def handle_weather(self, message: Message) -> None:
        """معالجة استفسار حالة الطقس"""
        response = random.choice(self.weather_dialogs)
        self.speak(response)
