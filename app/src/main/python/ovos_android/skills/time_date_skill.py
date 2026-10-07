# -*- coding: utf-8 -*-
"""
مهارة الوقت والتاريخ (TimeDateSkill)
تحسب الوقت الفعلي وتاريخ اليوم وتقدمه بصيغة عربية ملائمة للنطق الصوتي
"""

from datetime import datetime
from ..skill import OVOSSkill, intent_handler
from ..message import Message

class TimeDateSkill(OVOSSkill):
    """مهارة قراءة الوقت والتاريخ باللغة العربية"""

    def __init__(self, bus):
        super().__init__("time_date_skill", bus)
        self.arabic_weekdays = {
            0: "الإثنين", 1: "الثلاثاء", 2: "الأربعاء", 3: "الخميس",
            4: "الجمعة", 5: "السبت", 6: "الأحد"
        }
        self.arabic_months = {
            1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل",
            5: "مايو", 6: "يونيو", 7: "يوليو", 8: "أغسطس",
            9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
        }

    @intent_handler("time_date_skill")
    def handle_time_date(self, message: Message) -> None:
        """معالجة استفسار الوقت والتاريخ"""
        now = datetime.now()
        hour = now.hour
        period = "صباحاً" if hour < 12 else "مساءً"
        display_hour = hour if hour <= 12 else hour - 12
        display_hour = 12 if display_hour == 0 else display_hour
        minute = now.minute

        weekday_name = self.arabic_weekdays.get(now.weekday(), "")
        month_name = self.arabic_months.get(now.month, "")

        time_str = f"{display_hour} و{minute:02d} دقيقة {period}"
        date_str = f"اليوم هو {weekday_name}، {now.day} من {month_name} لعام {now.year}"

        utterance = message.data.get("utterance", "")
        if "تاريخ" in utterance or "يوم" in utterance:
            response = f"{date_str}، والساعة الآن هي {time_str}."
        else:
            response = f"الساعة الآن هي {time_str}."

        self.speak(response)
