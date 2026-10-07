# -*- coding: utf-8 -*-
"""
مهارات المعرفة والعلوم والمهام اليومية المشتقة من مجموعة البيانات العربية
تتفاعل مع النوايا التخصصية وتقدم إجابات علمية وثقافية مسترجعة من النموذج المحلي وقواعد البيانات
مع دعم الاستعلام اللحظي الذكي من موسوعة ويكيبيديا العربية والأخبار الحية
"""

import os
import re
import json
import random
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Optional
from ..skill import OVOSSkill, intent_handler
from ..message import Message
from ..text_sanitizer import TextSanitizer

ARABIC_QUERY_STOPWORDS = {
    "ما", "ماذا", "من", "هل", "كيف", "اين", "متى", "كم", "لماذا", "هو", "هي", "هم",
    "في", "على", "عن", "من", "الى", "الي", "مع", "هذا", "هذه", "ذلك", "تلك", "ان",
    "انني", "كان", "كانت", "يكون", "تكون", "شنو", "شلون", "منو", "وين", "ليش", "هسا",
    "اريد", "اعطني", "انطيني", "حدثني", "اشرح", "صف", "عرف", "الف", "اكتب", "سويلي", "يا",
    "ماهو", "ماهي", "عاصمة", "عاصمه"
}

ARAB_AND_WORLD_CAPITALS = {
    "العراق": "بغداد", "عراق": "بغداد",
    "السعودية": "الرياض", "المملكة العربية السعودية": "الرياض", "سعودية": "الرياض",
    "مصر": "القاهرة", "جمهورية مصر العربية": "القاهرة",
    "سوريا": "دمشق", "سورية": "دمشق",
    "الأردن": "عمان", "الاردن": "عمان",
    "لبنان": "بيروت",
    "فلسطين": "القدس الشريف",
    "الإمارات": "أبوظبي", "الامارات": "أبوظبي", "الإمارات العربية المتحدة": "أبوظبي",
    "الكويت": "مدينة الكويت",
    "قطر": "الدوحة",
    "البحرين": "المنامة",
    "عمان": "مسقط", "سلطنة عمان": "مسقط",
    "اليمن": "صنعاء",
    "السودان": "الخرطوم",
    "ليبيا": "طرابلس",
    "تونس": "تونس العاصمة",
    "الجزائر": "الجزائر العاصمة",
    "المغرب": "الرباط",
    "موريتانيا": "نواكشوط",
    "الصومال": "مقديشو",
    "جيبوتي": "مدينة جيبوتي",
    "جزر القمر": "موروني",
    "فرنسا": "باريس",
    "بريطانيا": "لندن", "المملكة المتحدة": "لندن", "إنجلترا": "لندن", "انجلترا": "لندن",
    "ألمانيا": "برلين", "المانيا": "برلين",
    "إيطاليا": "روما", "ايطاليا": "روما",
    "إسبانيا": "مدريد", "اسبانيا": "مدريد",
    "روسيا": "موسكو",
    "الصين": "بكين",
    "اليابان": "طوكيو",
    "الولايات المتحدة": "واشنطن العاصمة", "أمريكا": "واشنطن العاصمة", "امريكا": "واشنطن العاصمة", "الولايات المتحدة الأمريكية": "واشنطن العاصمة",
    "كندا": "أوتاوا",
    "أستراليا": "كانبرا", "استراليا": "كانبرا",
    "تركيا": "أنقرة", "انقرة": "أنقرة",
    "إيران": "طهران", "ايران": "طهران",
    "الهند": "نيودلهي",
    "باكستان": "إسلام آباد",
    "إندونيسيا": "جاكرتا", "اندونيسيا": "جاكرتا",
    "ماليزيا": "كوالالمبور",
    "البرازيل": "برازيليا",
    "الأرجنتين": "بوينس آيرس", "الارجنتين": "بوينس آيرس",
    "المكسيك": "مكسيكو سيتي",
    "جنوب أفريقيا": "بريتوريا", "جنوب افريقيا": "بريتوريا",
    "كوريا الجنوبية": "سيول", "كوريا": "سيول",
    "كوريا الشمالية": "بيونغ يانغ",
    "هولندا": "أمستردام",
    "بلجيكا": "بروكسل",
    "سويسرا": "برن",
    "النمسا": "فيينا",
    "السويد": "ستوكهولم",
    "النرويج": "أوسلو",
    "الدنمارك": "كوبنهاغن",
    "فنلندا": "هلسنكي",
    "اليونان": "أثينا",
    "البرتغال": "لشبونة",
    "بولندا": "وارسو",
    "أوكرانيا": "كييف", "اوكرانيا": "كييف"
}

def query_wikipedia_arabic(query_text: str) -> Optional[str]:
    """استعلام فوري من موسوعة ويكيبيديا العربية للحصول على معلومات مؤكدة ودقيقة"""
    try:
        clean_q = re.sub(r'^(ما هو|ما هي|من هو|من هي|عرف|اشرح|اين يقع|ماذا عن|عن|كم|كيف|ماهو|ماهي)\s*', '', query_text.strip()).strip()
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
                return TextSanitizer.clean_for_speech(res)
    except Exception:
        pass
    return None

def fetch_live_arabic_news() -> Optional[str]:
    """جلب آخر العناوين الإخبارية الحية من خدمة الأخبار باللغة العربية"""
    try:
        url = 'https://news.google.com/rss?hl=ar&gl=SA&ceid=SA:ar'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            content = resp.read(65536).decode('utf-8', errors='ignore')
            titles = re.findall(r'<item>\s*<title>([^<]+)</title>', content)
            headlines = []
            for t in titles[:2]:
                clean_t = re.sub(r'\s*-\s*[^-]+$', '', t).strip()
                headlines.append(clean_t)
            if headlines:
                return TextSanitizer.clean_for_speech(
                    f"إليك أبرز عناوين الأخبار اليوم: أولاً، {headlines[0]}. ثانياً، {headlines[1]}."
                )
    except Exception:
        pass
    return None

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

def find_best_response_in_cluster(utterance: str, qa_list: List[Dict[str, str]], fallback_responses: Optional[List[str]] = None) -> Optional[str]:
    """
    إيجاد الإجابة الأكثر دلالية لسؤال المستخدم بالاعتماد على الأوزان المعنوية للكلمات
    وتجاوز التنوع اللفظي والسوابق وحروف الجر، مع اشتراط تطابق المعنى الجوهري
    """
    if not qa_list:
        if fallback_responses:
            return TextSanitizer.clean_for_speech(random.choice(fallback_responses))
        return None

    clean_raw = re.sub(r'[^\w\s]', ' ', utterance)
    raw_words = [w.strip() for w in clean_raw.split() if w.strip()]
    content_roots = {_normalize_word(w) for w in raw_words if w not in ARABIC_QUERY_STOPWORDS and len(_normalize_word(w)) >= 2}

    if not content_roots:
        if fallback_responses:
            return TextSanitizer.clean_for_speech(random.choice(fallback_responses))
        return None

    best_item = None
    best_score = 0.0

    for item in qa_list:
        q_text = item.get("instruction", "")
        q_clean = re.sub(r'[^\w\s]', ' ', q_text)
        q_raw_words = [w.strip() for w in q_clean.split() if w.strip()]
        q_roots = {_normalize_word(w) for w in q_raw_words if w not in ARABIC_QUERY_STOPWORDS and len(_normalize_word(w)) >= 2}

        # احتساب نقاط التطابق المعنوي (Semantic Content Match)
        overlap = len(content_roots.intersection(q_roots))
        if overlap > best_score:
            best_score = overlap
            best_item = item

    # اشتراط تطابق كلمتين جوهريتين على الأقل لمنع الإجابات العشوائية الخاطئة
    threshold = max(2.0, len(content_roots) * 0.5)
    if best_item and best_score >= threshold:
        return TextSanitizer.clean_for_speech(best_item["response"])
    elif fallback_responses:
        return TextSanitizer.clean_for_speech(random.choice(fallback_responses))
    return None


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
        resp = find_best_response_in_cluster(utt, self.qa_pairs, None)
        if resp:
            self.speak(resp)
            return

        wiki = query_wikipedia_arabic(utt)
        if wiki:
            self.speak(wiki)
            return

        self.speak(TextSanitizer.clean_for_speech(random.choice(self.default_responses)))


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

        # 1. الاستعلام الفوري والمؤكد لعواصم الدول العربية والعالمية
        if any(w in utt for w in ["عاصمة", "عاصمه"]):
            for country in sorted(ARAB_AND_WORLD_CAPITALS.keys(), key=len, reverse=True):
                if country in utt:
                    capital = ARAB_AND_WORLD_CAPITALS[country]
                    self.speak(TextSanitizer.clean_for_speech(f"عاصمة {country} هي {capital}."))
                    return

        # 2. فحص قاعدة البيانات المحلية بتطابق موضوعي عالي
        resp = find_best_response_in_cluster(utt, self.qa_pairs, None)
        if resp:
            self.speak(resp)
            return

        # 3. الاستعلام اللحظي من موسوعة ويكيبيديا العربية
        wiki = query_wikipedia_arabic(utt)
        if wiki:
            self.speak(wiki)
            return

        self.speak(TextSanitizer.clean_for_speech(random.choice(self.default_responses)))


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
        
        # تجربة حل العمليات الحسابية المباشرة (مثل 5 * 12 أو 25 في 4 أو 10 + 20)
        calc_match = re.search(r'(\d+(?:\.\d+)?)\s*([+\-*xX×÷/]|في|ضرب|زائد|ناقص|قسمة|قسمه|على)\s*(\d+(?:\.\d+)?)', utt)
        if calc_match:
            n1 = float(calc_match.group(1))
            op = calc_match.group(2)
            n2 = float(calc_match.group(3))
            res = None
            if op in ['+', 'زائد']:
                res = n1 + n2
            elif op in ['-', 'ناقص']:
                res = n1 - n2
            elif op in ['*', 'x', 'X', '×', 'ضرب', 'في']:
                res = n1 * n2
            elif op in ['/', '÷', 'قسمة', 'قسمه', 'على'] and n2 != 0:
                res = n1 / n2

            if res is not None:
                res_str = f"{res:.2f}".rstrip('0').rstrip('.')
                self.speak(TextSanitizer.clean_for_speech(f"ناتج العملية الحسابية هو: {res_str}"))
                return

        resp = find_best_response_in_cluster(utt, self.qa_pairs, None)
        if resp:
            self.speak(resp)
            return

        wiki = query_wikipedia_arabic(utt)
        if wiki:
            self.speak(wiki)
            return

        self.speak(TextSanitizer.clean_for_speech(random.choice(self.default_responses)))


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
        resp = find_best_response_in_cluster(utt, self.qa_pairs, None)
        if resp:
            self.speak(resp)
            return

        wiki = query_wikipedia_arabic(utt)
        if wiki:
            self.speak(wiki)
            return

        self.speak(TextSanitizer.clean_for_speech(random.choice(self.default_responses)))


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

        # 1. الاستعلام عن آخر الأخبار الحية
        if any(w in utt for w in ["اخر الاخبار", "آخر الأخبار", "أخبار", "اخبار", "عناوين الاخبار", "الجديد في العالم"]):
            news = fetch_live_arabic_news()
            if news:
                self.speak(news)
                return

        # 2. فحص قاعدة البيانات المحلية
        resp = find_best_response_in_cluster(utt, self.qa_pairs, None)
        if resp:
            self.speak(resp)
            return

        # 3. الاستعلام من موسوعة ويكيبيديا العربية
        wiki = query_wikipedia_arabic(utt)
        if wiki:
            self.speak(wiki)
            return

        self.speak(TextSanitizer.clean_for_speech(random.choice(self.default_responses)))
