# -*- coding: utf-8 -*-
"""
مهارة التراجع والمعارف العامة الاحتياطية (Enhanced FallbackSkill)
تتولى معالجة العبارات عند عدم وضوح النية عبر:
1. الاستعلام المباشر من DuckDuckGo Instant Answer API.
2. الاستعلام من Wolfram Alpha Spoken API (عند توفر مفتاح التطبيق).
3. التراجع الآمن إلى قاعدة الأسئلة والأجوبة المحلية مع المطابقة التقريبية.
4. التنقية الصارمة عبر TextSanitizer لمنع تسرب وسوم الويب أو الأسطر.
"""

import os
import re
import json
import random
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Optional

from ..skill import OVOSSkill
from ..message import Message
from ..text_sanitizer import TextSanitizer


class FallbackSkill(OVOSSkill):
    """مهارة التراجع الذكية والمعارف الموسعة"""

    def __init__(self, bus, qa_pairs: Optional[List[Dict[str, str]]] = None):
        super().__init__("fallback_skill", bus)
        self.qa_pairs = qa_pairs or []
        self.wolfram_app_id = os.environ.get("WOLFRAM_APP_ID", "")
        self.polite_fallbacks = [
            "عذراً، لم أستطع العثور على إجابة دقيقة لسؤالك. هل يمكنك إعادة صياغته بكلمات أخرى؟",
            "لم تتضح لي الإجابة الكاملة، يرجى سؤالي بطريقة أوضح وسأبذل جهدي لمساعدتك.",
            "أنا أتعلم باستمرار، لم أتعرف على هذا الطلب بدقة، هل تود السؤال عن شيء آخر؟"
        ]

    def _query_duckduckgo(self, query: str) -> Optional[str]:
        """الاستعلام من DuckDuckGo Instant Answer API"""
        try:
            encoded_q = urllib.parse.quote(query.strip())
            url = f"https://api.duckduckgo.com/?q={encoded_q}&format=json&no_html=1&skip_disambig=1"
            req = urllib.request.Request(url, headers={"User-Agent": "BYD-DiLink-VoiceAssistant/2.0"})
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                abstract = data.get("AbstractText", "").strip()
                if abstract:
                    return abstract
                answer = data.get("Answer", "").strip()
                if answer:
                    return answer
        except Exception:
            pass
        return None

    def _query_wolfram_alpha(self, query: str) -> Optional[str]:
        """الاستعلام من Wolfram Alpha Spoken API"""
        if not self.wolfram_app_id:
            return None
        try:
            encoded_q = urllib.parse.quote(query.strip())
            url = f"https://api.wolframalpha.com/v1/spoken?appid={self.wolfram_app_id}&i={encoded_q}"
            req = urllib.request.Request(url, headers={"User-Agent": "BYD-DiLink-VoiceAssistant/2.0"})
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                return resp.read().decode("utf-8").strip()
        except Exception:
            pass
        return None

    def handle_fallback(self, message: Message) -> None:
        """معالجة التراجع: محاولة البحث عبر الإنترنت أولاً ثم قاعدة البيانات المحلية"""
        utterance = message.data.get("utterance", "")
        if not utterance:
            self.speak(TextSanitizer.clean_for_speech(random.choice(self.polite_fallbacks)))
            return

        # 1. الاستعلام عبر Wolfram Alpha إن كان مفعلًا
        wolfram_result = self._query_wolfram_alpha(utterance)
        if wolfram_result:
            self.speak(TextSanitizer.clean_for_speech(wolfram_result))
            return

        # 2. الاستعلام عبر DuckDuckGo
        ddg_result = self._query_duckduckgo(utterance)
        if ddg_result:
            self.speak(TextSanitizer.clean_for_speech(ddg_result))
            return

        # 3. التراجع لقاعدة الأسئلة والأجوبة المحلية
        words = set(re.sub(r'[^\w\s]', '', utterance).split())
        best_match = None
        best_score = 0

        for item in self.qa_pairs:
            q_words = set(re.sub(r'[^\w\s]', '', item.get("instruction", "")).split())
            overlap = len(words.intersection(q_words))
            if overlap > best_score:
                best_score = overlap
                best_match = item

        if best_match and best_score >= 2:
            self.speak(TextSanitizer.clean_for_speech(best_match["response"]))
        else:
            self.speak(TextSanitizer.clean_for_speech(random.choice(self.polite_fallbacks)))
