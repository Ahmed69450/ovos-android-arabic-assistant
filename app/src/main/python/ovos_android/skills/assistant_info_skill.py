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
        """تقديم تعريف شامل عن المساعد الصوتي العربي وطريقة عمله"""
        utt = message.data.get("utterance", "")
        if any(w in utt for w in ["كيف تعمل", "كيف تشتغل", "طريقة عملك", "التقنية", "كيف تم تطويرك", "التقنيه"]):
            response = (
                "أعمل عبر معمارية هجينة تجمع بين محرك التعرف الصوتي Vosk، وخوارزميات الفهم اللغوي الطبيعي NLU، "
                "مع آلة حالات الحوار FSM لإدارة السياق، ومحرك النطق Piper TTS. كل هذه المكونات تعمل محلياً "
                "بالكامل على هاتفك دون استهلاك للإنترنت أو إرهاق للمعالج."
            )
        else:
            response = (
                "أنا مساعدك الصوتي الذكي المبني على معمارية OpenVoiceOS المخصصة لنظام أندرويد. "
                "أعمل محلياً بالكامل على هاتفك دون الحاجة إلى خوادم سحابية، مما يضمن لك الخصوصية التامة "
                "وسرعة الاستجابة اللحظية في فهم النوايا وتنفيذ المهارات."
            )
        self.speak(response)
