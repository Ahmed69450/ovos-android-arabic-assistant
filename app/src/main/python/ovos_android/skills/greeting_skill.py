# -*- coding: utf-8 -*-
"""
مهارة التحية والترحيب (GreetingSkill)
تستقبل التحيات وتجيب بعبارات ترحيبية عربية ودودة
"""

import random
from ..skill import OVOSSkill, intent_handler
from ..message import Message

class GreetingSkill(OVOSSkill):
    """مهارة OVOS للتعامل مع التحيات والاستقبال وتبادل أطراف الحديث (Chitchat)"""

    def __init__(self, bus):
        super().__init__("greeting_skill", bus)
        self.greetings = [
            "أهلاً وسهلاً بك! أنا مساعدك الصوتي الذكي، كيف يمكنني مساعدتك اليوم؟",
            "وعليكم السلام ورحمة الله وبركاته! يسعدني جداً التحدث معك.",
            "مرحباً بك! أتمنى أن تكون في أتم الصحة والعافية، ما الذي تود القيام به؟",
            "أهلاً صديقي! أنا جاهز للإجابة على أسئلتك ومساعدتك في أي وقت."
        ]
        self.status_replies = [
            "دومك بخير وصحة يا رب! شلون أقدر أساعدك اليوم؟",
            "الحمد لله دائماً! يسعدني أنك بخير، بأي موضوع حاب نتكلم أو أساعدك؟",
            "عساك دوم بأفضل حال ونشاط! شنو في بالك لليوم؟"
        ]

    @intent_handler("greeting_skill")
    def handle_greeting(self, message: Message) -> None:
        """معالجة نية التحية وبث الرد الصوتي مع تمييز ردود الحالة الشخصية (Chitchat)"""
        utt = message.data.get("utterance", "")
        match_type = message.data.get("match_type", "")

        chitchat_markers = [
            "زين", "بخير", "تمام", "الحمد لله", "الحمدلله", "عايشين",
            "ماشي الحال", "كويس", "بصحة جيدة", "على ما يرام", "طيب"
        ]

        if match_type == "chitchat_followup" or any(m in utt for m in chitchat_markers):
            response = random.choice(self.status_replies)
        else:
            response = random.choice(self.greetings)
        self.speak(response)
