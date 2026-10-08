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


def is_explicit_knowledge_query(query: str) -> bool:
    """التحقق مما إذا كانت العبارة سؤالاً معرفياً صريحاً وليست دردشة أو كلاماً عاماً"""
    q = query.strip()
    explicit_prefixes = (
        "من هو", "من هي", "ما هو", "ما هي", "ماهو", "ماهي",
        "عرف لي", "عرف ", "اشرح لي", "اشرح ", "حدثني عن", "نبذة عن",
        "معلومات عن", "اين يقع", "اين تقع", "وين صاير", "وين صايرة",
        "من اخترع", "من صنع", "من اكتشف", "من بنى", "متى حدث", "ما معنى",
        "شنو معنى", "شنو هو", "شنو هي", "ما سبب", "كيف يحدث", "كيف تكونت"
    )
    return any(q.startswith(p) for p in explicit_prefixes)


class FallbackSkill(OVOSSkill):
    """مهارة التراجع الصارمة والآمنة من الهلوسة (Strict Fallback)"""

    def __init__(self, bus, qa_pairs: Optional[List[Dict[str, str]]] = None):
        super().__init__("fallback_skill", bus)
        self.qa_pairs = qa_pairs or []
        self.wolfram_app_id = os.environ.get("WOLFRAM_APP_ID", "")
        self.polite_fallbacks = [
            "عذراً، ما فهمت قصدك، تكدر تعيد؟",
            "ما وضحت لي الفكرة، يا ريت تعيد صياغة السؤال.",
            "عذراً، ما عرفت شنو قصدك بالضبط، تكدر توضح أكثر؟"
        ]

    def _query_duckduckgo(self, query: str) -> Optional[str]:
        """الاستعلام من DuckDuckGo Instant Answer API"""
        try:
            encoded_q = urllib.parse.quote(query.strip())
            url = f"https://api.duckduckgo.com/?q={encoded_q}&format=json&no_html=1&skip_disambig=1"
            req = urllib.request.Request(url, headers={"User-Agent": "BYD-DiLink-VoiceAssistant/2.0"})
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read(65536).decode("utf-8"))
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
                return resp.read(65536).decode("utf-8").strip()
        except Exception:
            pass
        return None

    def _query_wikipedia(self, query: str) -> Optional[str]:
        """الاستعلام من موسوعة ويكيبيديا العربية للأسئلة المعرفية والعامة"""
        try:
            clean_q = re.sub(r'^(ما هو|ما هي|من هو|من هي|عرف|اشرح|اين يقع|ماذا عن|عن|كم|كيف|ماهو|ماهي)\s*', '', query.strip()).strip()
            clean_q = re.sub(r'[^\w\s]', '', clean_q).strip()
            if not clean_q or len(clean_q) < 2:
                return None
            search_url = f"https://ar.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(clean_q)}&utf8=1&format=json"
            req = urllib.request.Request(search_url, headers={"User-Agent": "BYD-DiLink-VoiceAssistant/2.1"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read(65536).decode("utf-8"))
                results = data.get("query", {}).get("search", [])
                if not results:
                    return None
                title = results[0]["title"]

            sum_url = f"https://ar.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
            s_req = urllib.request.Request(sum_url, headers={"User-Agent": "BYD-DiLink-VoiceAssistant/2.1"})
            with urllib.request.urlopen(s_req, timeout=3.0) as s_resp:
                s_data = json.loads(s_resp.read(65536).decode("utf-8"))
                extract = s_data.get("extract", "").strip()
                if extract:
                    sentences = re.split(r'[\.\n]\s*', extract)
                    res = '. '.join([s.strip() for s in sentences[:2] if len(s.strip()) > 10]) + '.'
                    return res
        except Exception:
            pass
        return None

    def handle_fallback(self, message: Message) -> None:
        """معالجة التراجع: فحص قاعدة المعرفة المحلية المباشرة أولاً ثم البحث عبر ويكيبيديا وDuckDuckGo"""
        utterance = message.data.get("utterance", "")
        if not utterance:
            self.speak(TextSanitizer.clean_for_speech(random.choice(self.polite_fallbacks)))
            return

        # 1. فحص قاعدة الأسئلة والأجوبة المحلية المباشرة عند وجود تطابق عالي
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
            return

        # 2. الاستعلام عبر ويكيبيديا أو محركات البحث فقط إذا كان السؤال استفساراً معرفياً صريحاً
        if is_explicit_knowledge_query(utterance):
            wiki_result = self._query_wikipedia(utterance)
            if wiki_result:
                self.speak(TextSanitizer.clean_for_speech(wiki_result))
                return

            wolfram_result = self._query_wolfram_alpha(utterance)
            if wolfram_result:
                self.speak(TextSanitizer.clean_for_speech(wolfram_result))
                return

            ddg_result = self._query_duckduckgo(utterance)
            if ddg_result:
                self.speak(TextSanitizer.clean_for_speech(ddg_result))
                return

        # 3. التراجع الصارم (Strict Fallback) الخالي تماماً من الهلوسة
        self.speak(TextSanitizer.clean_for_speech(random.choice(self.polite_fallbacks)))
