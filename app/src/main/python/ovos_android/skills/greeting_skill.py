# -*- coding: utf-8 -*-
"""
مهارة التحية والترحيب (GreetingSkill)
تستقبل التحيات وتجيب بعبارات ترحيبية عربية ودودة
"""

import random
from ..skill import OVOSSkill, intent_handler
from ..message import Message

class GreetingSkill(OVOSSkill):
    """مهارة OVOS للتعامل مع التحيات والاستقبال"""

    def __init__(self, bus):
        super().__init__("greeting_skill", bus)
        self.greetings = [
            "أهلاً وسهلاً بك! أنا مساعدك الصوتي الذكي، كيف يمكنني مساعدتك اليوم؟",
            "وعليكم السلام ورحمة الله وبركاته! يسعدني جداً التحدث معك.",
            "مرحباً بك! أتمنى أن تكون في أتم الصحة والعافية، ما الذي تود القيام به؟",
            "أهلاً صديقي! أنا جاهز للإجابة على أسئلتك ومساعدتك في أي وقت."
        ]

    @intent_handler("greeting_skill")
    def handle_greeting(self, message: Message) -> None:
        """معالجة نية التحية وبث الرد الصوتي"""
        response = random.choice(self.greetings)
        self.speak(response)
