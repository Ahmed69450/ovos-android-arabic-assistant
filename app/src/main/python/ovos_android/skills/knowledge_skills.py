# -*- coding: utf-8 -*-
"""
مهارات المعرفة والعلوم والمهام اليومية المشتقة من مجموعة البيانات العربية
تتفاعل مع النوايا التخصصية وتقدم إجابات علمية وثقافية مسترجعة من النموذج المحلي
"""

import re
import random
from typing import List, Dict, Any, Optional
from ..skill import OVOSSkill, intent_handler
from ..message import Message
from ..text_sanitizer import TextSanitizer

ARABIC_QUERY_STOPWORDS = {
    "ما", "ماذا", "من", "هل", "كيف", "اين", "متى", "كم", "لماذا", "هو", "هي", "هم",
    "في", "على", "عن", "من", "الى", "الي", "مع", "هذا", "هذه", "ذلك", "تلك", "ان",
    "انني", "كان", "كانت", "يكون", "تكون", "شنو", "شلون", "منو", "وين", "ليش", "هسا",
    "اريد", "اعطني", "انطيني", "حدثني", "اشرح", "صف", "عرف", "الف", "اكتب", "سويلي", "يا"
}

def _normalize_word(w: str) -> str:
    """تنقية وتوحيد الكلمة العربية وإزالة السوابق"""
    w = re.sub(r'[\u064B-\u065F\u0670\u0640]', '', w)
    w = re.sub(r'[إأآا]', 'ا', w)
    w = re.sub(r'[يى]', 'ي', w)
    w = re.sub(r'ة', 'ه', w)
    for p in ('وال', 'فال', 'بال', 'كال', 'لل', 'ال', 'و', 'ف', 'ب', 'ل', 'ك'):
        if w.startswith(p) and len(w) - len(p) >= 3:
            return w[len(p):]
    return w

def find_best_response_in_cluster(utterance: str, qa_list: List[Dict[str, str]], fallback_responses: List[str]) -> str:
    """
    إيجاد الإجابة الأكثر دلالية لسؤال المستخدم بالاعتماد على الأوزان المعنوية للكلمات
    وتجاوز التنوع اللفظي والسوابق وحروف الجر
    """
    if not qa_list:
        raw = random.choice(fallback_responses) if fallback_responses else "تم استلام طلبك بنجاح."
        return TextSanitizer.clean_for_speech(raw)

    clean_raw = re.sub(r'[^\w\s]', ' ', utterance)
    raw_words = [w.strip() for w in clean_raw.split() if w.strip()]
    content_roots = {_normalize_word(w) for w in raw_words if w not in ARABIC_QUERY_STOPWORDS}

    best_item = None
    best_score = 0.0

    for item in qa_list:
        q_text = item.get("instruction", "")
        q_clean = re.sub(r'[^\w\s]', ' ', q_text)
        q_raw_words = [w.strip() for w in q_clean.split() if w.strip()]
        q_roots = {_normalize_word(w) for w in q_raw_words if w not in ARABIC_QUERY_STOPWORDS}

        # احتساب نقاط التطابق المعنوي (Semantic Content Match)
        overlap = len(content_roots.intersection(q_roots))
        if overlap > best_score:
            best_score = overlap
            best_item = item

    if best_item and best_score >= 1.0:
        return TextSanitizer.clean_for_speech(best_item["response"])
    elif fallback_responses:
        return TextSanitizer.clean_for_speech(random.choice(fallback_responses))
    elif best_item:
        return TextSanitizer.clean_for_speech(best_item["response"])
    return TextSanitizer.clean_for_speech(qa_list[0]["response"])


class HealthWellnessSkill(OVOSSkill):
    """مهارة الصحة والتغذية ونمط الحياة"""
    def __init__(self, bus, qa_pairs=None, default_responses=None):
        super().__init__("health_wellness_skill", bus)
        self.qa_pairs = qa_pairs or []
        self.default_responses = default_responses or [
            "للحفاظ على صحة ممتازة، يُنصح بتناول وجبات غذائية متوازنة، شرب كميات وافرة من الماء، وممارسة الرياضة يومياً لمدة 30 دقيقة."
        ]

    @intent_handler("health_wellness_skill")
    def handle_health(self, message: Message):
        utt = message.data.get("utterance", "")
        resp = find_best_response_in_cluster(utt, self.qa_pairs, self.default_responses)
        self.speak(resp)


class ScienceTechSkill(OVOSSkill):
    """مهارة العلوم والتكنولوجيا والفيزياء والبرمجة"""
    def __init__(self, bus, qa_pairs=None, default_responses=None):
        super().__init__("science_tech_skill", bus)
        self.qa_pairs = qa_pairs or []
        self.default_responses = default_responses or [
            "العلوم والتكنولوجيا هي المحرك الأساسي للابتكار، وتعتمد على التجارب والملاحظة لفهم العالم وتطوير الحلول البرمجية والهندسية."
        ]

    @intent_handler("science_tech_skill")
    def handle_science(self, message: Message):
        utt = message.data.get("utterance", "")
        resp = find_best_response_in_cluster(utt, self.qa_pairs, self.default_responses)
        self.speak(resp)


class HistoryGeographySkill(OVOSSkill):
    """مهارة التاريخ والجغرافيا والدول والعواصم"""
    def __init__(self, bus, qa_pairs=None, default_responses=None):
        super().__init__("history_geography_skill", bus)
        self.qa_pairs = qa_pairs or []
        self.default_responses = default_responses or [
            "يقدم التاريخ نظرة عميقة على مسار الحضارات الإنسانية وتطور المدن والدول عبر العصور."
        ]

    @intent_handler("history_geography_skill")
    def handle_history(self, message: Message):
        utt = message.data.get("utterance", "")
        resp = find_best_response_in_cluster(utt, self.qa_pairs, self.default_responses)
        self.speak(resp)


class MathLogicSkill(OVOSSkill):
    """مهارة العمليات الحسابية والمنطق والرياضيات"""
    def __init__(self, bus, qa_pairs=None, default_responses=None):
        super().__init__("math_logic_skill", bus)
        self.qa_pairs = qa_pairs or []
        self.default_responses = default_responses or [
            "الرياضيات هي لغة المنطق والدقة، ويمكن حل المسائل الرياضية باتباع القواعد الحسابية والترتيب المنطقي للعمليات."
        ]

    @intent_handler("math_logic_skill")
    def handle_math(self, message: Message):
        utt = message.data.get("utterance", "")
        
        # تجربة حل العمليات الحسابية المباشرة (مثل 5 * 12 أو 10 + 20)
        calc_match = re.search(r'(\d+)\s*([+\-*xX×÷/])\s*(\d+)', utt)
        if calc_match:
            n1 = float(calc_match.group(1))
            op = calc_match.group(2)
            n2 = float(calc_match.group(3))
            res = None
            if op in ['+', 'زائد']:
                res = n1 + n2
            elif op in ['-', 'ناقص']:
                res = n1 - n2
            elif op in ['*', 'x', 'X', '×', 'ضرب']:
                res = n1 * n2
            elif op in ['/', '÷', 'قسمة'] and n2 != 0:
                res = n1 / n2

            if res is not None:
                res_str = f"{res:.2f}".rstrip('0').rstrip('.')
                self.speak(TextSanitizer.clean_for_speech(f"ناتج العملية الحسابية هو: {res_str}"))
                return

        resp = find_best_response_in_cluster(utt, self.qa_pairs, self.default_responses)
        self.speak(resp)


class LanguageTranslationSkill(OVOSSkill):
    """مهارة اللغة والمفردات والترجمة اللغوية"""
    def __init__(self, bus, qa_pairs=None, default_responses=None):
        super().__init__("language_translation_skill", bus)
        self.qa_pairs = qa_pairs or []
        self.default_responses = default_responses or [
            "اللغة العربية غنية بالمفردات والمعاني والترادفات البلاغية الدقيقة."
        ]

    @intent_handler("language_translation_skill")
    def handle_language(self, message: Message):
        utt = message.data.get("utterance", "")
        resp = find_best_response_in_cluster(utt, self.qa_pairs, self.default_responses)
        self.speak(resp)


class CreativeWritingSkill(OVOSSkill):
    """مهارة التأليف الإبداعي والقصص والنصوص"""
    def __init__(self, bus, qa_pairs=None, default_responses=None):
        super().__init__("creative_writing_skill", bus)
        self.qa_pairs = qa_pairs or []
        self.default_responses = default_responses or [
            "في قديم الزمان، كانت هناك بلدة هادئة بين الجبال، يتعلم أهلها فنون الحكمة والتعاون مع الطبيعة."
        ]

    @intent_handler("creative_writing_skill")
    def handle_creative(self, message: Message):
        utt = message.data.get("utterance", "")
        resp = find_best_response_in_cluster(utt, self.qa_pairs, self.default_responses)
        self.speak(resp)


class DailyAssistantSkill(OVOSSkill):
    """مهارة النصائح اليومية وتنظيم المهام والقوائم"""
    def __init__(self, bus, qa_pairs=None, default_responses=None):
        super().__init__("daily_assistant_skill", bus)
        self.qa_pairs = qa_pairs or []
        self.default_responses = default_responses or [
            "إليك أهم الخطوات لتنظيم يومك بنجاح: حدد الأولويات في الصباح، قسّم المهام الكبيرة إلى خطوات صغيرة، وخذ فترات راحة قصيرة."
        ]

    @intent_handler("daily_assistant_skill")
    def handle_daily(self, message: Message):
        utt = message.data.get("utterance", "")
        resp = find_best_response_in_cluster(utt, self.qa_pairs, self.default_responses)
        self.speak(resp)


class GeneralKnowledgeSkill(OVOSSkill):
    """مهارة المعرفة العامة والإجابة على التساؤلات المتنوعة"""
    def __init__(self, bus, qa_pairs=None, default_responses=None):
        super().__init__("general_knowledge_skill", bus)
        self.qa_pairs = qa_pairs or []
        self.default_responses = default_responses or [
            "المعرفة واسعة ومتنوعة، ويسعدني دائماً تقديم الإجابات والمعلومات التي تبحث عنها."
        ]

    @intent_handler("general_knowledge_skill")
    def handle_general(self, message: Message):
        utt = message.data.get("utterance", "")
        resp = find_best_response_in_cluster(utt, self.qa_pairs, self.default_responses)
        self.speak(resp)
