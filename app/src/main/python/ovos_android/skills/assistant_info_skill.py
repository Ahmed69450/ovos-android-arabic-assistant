# -*- coding: utf-8 -*-
"""
مهارة التعريف بالمساعد وقدراته (AssistantInfoSkill)
تشرح هوية المساعد ومعماريته المستندة إلى OpenVoiceOS وعمله دون اتصال
"""

from ..skill import OVOSSkill, intent_handler
from ..message import Message

class AssistantInfoSkill(OVOSSkill):
    """مهارة التعريف بالهوية والمعمارية"""

    def __init__(self, bus):
        super().__init__("assistant_info_skill", bus)

    @intent_handler("assistant_info_skill")
    def handle_info(self, message: Message) -> None:
        """تقديم تعريف شامل عن المساعد الصوتي العربي"""
        response = (
            "أنا مساعدك الصوتي الذكي المبني على معمارية OpenVoiceOS المخصصة لنظام أندرويد. "
            "أعمل محلياً بالكامل على هاتفك دون الحاجة إلى خوادم سحابية، مما يضمن لك الخصوصية التامة "
            "وسرعة الاستجابة اللحظية في فهم النوايا وتنفيذ المهارات."
        )
        self.speak(response)
