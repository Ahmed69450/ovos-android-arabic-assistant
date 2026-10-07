# -*- coding: utf-8 -*-
"""
مهارة الإيقاف والإلغاء (StopSkill)
توقف القراءة الصوتية وتعيد النظام إلى وضع الاستعداد، وهي ركيزة أساسية في معمارية OVOS
"""

import random
from ..skill import OVOSSkill, intent_handler
from ..message import Message

class StopSkill(OVOSSkill):
    """مهارة إيقاف العمليات الصوتية في أندرويد"""

    def __init__(self, bus):
        super().__init__("stop_skill", bus)
        self.stop_dialogs = [
            "حسناً، تم الإيقاف.",
            "تم الإلغاء، أنا في وضع الاستعداد.",
            "توقفت عن الكلام، يمكنك مناداتي متى شئت.",
            "أمرك، سأصمت الآن."
        ]

    @intent_handler("stop_skill")
    def handle_stop(self, message: Message) -> None:
        """معالجة أمر التوقف وبث حدث الإيقاف العام لنظام أندرويد"""
        # بث حدث الإيقاف العام لنظام الصوت في أندرويد
        self.bus.emit(Message("mycroft.stop"))
        response = random.choice(self.stop_dialogs)
        self.speak(response)
