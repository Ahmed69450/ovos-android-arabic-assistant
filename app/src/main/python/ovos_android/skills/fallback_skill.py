# -*- coding: utf-8 -*-
"""
مهارة التراجع الاحتياطية (FallbackSkill) المتوافقة مع ovos-core Fallback Service
تتولى معالجة العبارات عند تدني درجة ثقة المطابقة أو عدم تطابق أي نية رئيسية
"""

import re
import random
from typing import List, Dict, Any, Optional
from ..skill import OVOSSkill
from ..message import Message

class FallbackSkill(OVOSSkill):
    """مهارة التراجع الاحتياطية للمساعد الصوتي"""

    def __init__(self, bus, qa_pairs: Optional[List[Dict[str, str]]] = None):
        super().__init__("fallback_skill", bus)
        self.qa_pairs = qa_pairs or []
        self.polite_fallbacks = [
            "عذراً، لم أستطع فهم سؤالك بشكل كامل. هل يمكنك إعادة صياغته بكلمات أخرى؟",
            "لم تتضح لي الإجابة الدقيقة لهذا السؤال، يرجى سؤالي بطريقة أوضح وسأبذل جهدي لمساعدتك.",
            "أنا أتعلم باستمرار، لم أتعرف على هذا الطلب بدقة، هل تود السؤال عن شيء آخر؟"
        ]

    def handle_fallback(self, message: Message) -> None:
        """معالجة التراجع: فحص الأسئلة المشابهة في قاعدة البيانات قبل إظهار الرد الافتراضي"""
        utterance = message.data.get("utterance", "")
        if not utterance:
            self.speak(random.choice(self.polite_fallbacks))
            return

        words = set(re.sub(r'[^\w\s]', '', utterance).split())
        best_match = None
        best_score = 0

        for item in self.qa_pairs:
            q_words = set(re.sub(r'[^\w\s]', '', item.get("instruction", "")).split())
            overlap = len(words.intersection(q_words))
            if overlap > best_score:
                best_score = overlap
                best_match = item

        # إذا وجدنا تطابقاً معقولاً لكلمتين أو أكثر نستخدمه
        if best_match and best_score >= 2:
            self.speak(best_match["response"])
        else:
            self.speak(random.choice(self.polite_fallbacks))
