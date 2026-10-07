# -*- coding: utf-8 -*-
"""
محرك الفهم اللغوي الطبيعي (NLU) للغة العربية الهجين لسيارات BYD DiLink
يجمع بين خوارزمية مسافة ليفنشتاين (Levenshtein Distance) للمطابقة التقريبية وتصحيح الأخطاء،
ومصفوفات TF-IDF المدربة محلياً للاستدلال السريع، مع دعم الذاكرة السياقية (FSM).
"""

import os
import re
import json
import math
from typing import Dict, Any, List, Optional, Tuple


def levenshtein_similarity(s1: str, s2: str) -> float:
    """حساب نسبة التشابه المعيارية بمسافة ليفنشتاين [0.0 - 1.0]"""
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0

    # الحد الدفاعي لطول النص لمنع استنزاف المعالج (CWE-400 CPU Exhaustion DoS)
    if len(s1) > 256:
        s1 = s1[:256]
    if len(s2) > 256:
        s2 = s2[:256]

    m, n = len(s1), len(s2)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        s1_char = s1[i - 1]
        for j in range(1, n + 1):
            temp = dp[j]
            cost = 0 if s1_char == s2[j - 1] else 1
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + cost)
            prev = temp

    max_len = max(m, n)
    return 1.0 - (dp[n] / max_len)


class ArabicNLUEngine:
    """محرك NLU المحلي الهجين (TF-IDF + Levenshtein + Contextual FSM)"""

    # الأنماط المحورية الأساسية للمطابقة التقريبية في بيئة السيارة
    CORE_PATTERNS = {
        "stop_skill": [
            "توقف", "اسكت", "الغاء", "اخرس", "انهاء", "توقف عن الكلام",
            "اغلق", "كفى", "صمت", "قف", "الغي", "بس خلاص"
        ],
        "greeting_skill": [
            "مرحبا", "السلام عليكم", "صباح الخير", "مساء الخير", "اهلا وسهلا",
            "كيف حالك", "شو اخبارك", "تحياتي", "اهلا", "هلا وغلا"
        ],
        "time_date_skill": [
            "كم الساعة", "ما هو الوقت", "الوقت الان", "تاريخ اليوم",
            "اي يوم نحن", "كم الوقت الان", "ما هو تاريخ اليوم"
        ],
        "assistant_info_skill": [
            "من انت", "ما اسمك", "عرف عن نفسك", "ما هي قدراتك",
            "ماذا تفعل", "من صنعك", "كيف تعمل"
        ],
        "weather_skill": [
            "كيف الطقس", "حالة الجو", "هل ستمطر", "درجة الحرارة",
            "الطقس اليوم", "كيف الجو غدا", "توقعات الطقس", "الجو بارد", "الجو حار"
        ]
    }

    def __init__(
        self,
        weights_source: Optional[Any] = None,
        intents_data_path: Optional[Any] = None
    ):
        self.vocab: Dict[str, int] = {}
        self.idf: List[float] = []
        self.classes: List[str] = []
        self.weights: List[List[float]] = []
        self.bias: List[float] = []
        self.ngram_range: Tuple[int, int] = (1, 2)
        self.sublinear_tf: bool = True
        self.is_loaded: bool = False

        # قواميس الأنماط للمطابقة التقريبية
        self.intent_patterns: Dict[str, List[str]] = {
            k: [self.normalize_arabic(p) for p in v] for k, v in self.CORE_PATTERNS.items()
        }

        if intents_data_path:
            self.load_patterns(intents_data_path)

        if weights_source:
            self.load_model(weights_source)

    @staticmethod
    def normalize_arabic(text: Optional[str]) -> str:
        """معالجة وتوحيد الأحرف العربية وإزالة التشكيل والكشيدة"""
        if not text or not isinstance(text, str):
            return ""
        # إزالة التشكيل والحركات والكشيدة
        text = re.sub(r'[\u064B-\u065F\u0670\u0640]', '', text)
        # توحيد الألف
        text = re.sub(r'[إأآا]', 'ا', text)
        # توحيد الياء
        text = re.sub(r'[يى]', 'ي', text)
        # توحيد التاء المربوطة
        text = re.sub(r'ة', 'ه', text)
        # إزالة علامات الترقيم
        text = re.sub(r'[^\w\s]', ' ', text)
        # توحيد المسافات
        return ' '.join(text.split())

    def load_patterns(self, source: Any) -> None:
        """تحميل أنماط النوايا من ملف intents.json لدعم المطابقة التقريبية الشاملة"""
        try:
            if isinstance(source, str) and os.path.exists(source):
                with open(source, "r", encoding="utf-8") as f:
                    data = json.load(f)
            elif isinstance(source, dict):
                data = source
            else:
                return

            for intent in data.get("intents", []):
                tag = intent.get("tag")
                patterns = intent.get("patterns", [])
                if tag and patterns:
                    if tag not in self.intent_patterns:
                        self.intent_patterns[tag] = []
                    for pat in patterns[:50]:  # أفضل 50 نمط لكل نية لسرعة المعالجة
                        norm_p = self.normalize_arabic(pat)
                        if norm_p and norm_p not in self.intent_patterns[tag]:
                            self.intent_patterns[tag].append(norm_p)
        except Exception as e:
            print(f"[NLU Warning] Failed to load intent patterns: {e}")

    def load_model(self, source: Any) -> None:
        """تحميل أوزان نموذج TF-IDF من ملف JSON أو قاموس"""
        if isinstance(source, str):
            if os.path.exists(source):
                with open(source, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = json.loads(source)
        elif isinstance(source, dict):
            data = source
        else:
            raise ValueError("مصدر أوزان النموذج غير صالح.")

        self.vocab = data["vocabulary"]
        self.idf = data["idf"]
        self.classes = data["classes"]
        self.weights = data["weights"]
        self.bias = data["bias"]
        self.ngram_range = tuple(data.get("ngram_range", [1, 2]))
        self.sublinear_tf = bool(data.get("sublinear_tf", True))
        self.is_loaded = True

    def _tokenize(self, text: str) -> List[str]:
        """تفكيك الجملة إلى Unigrams و Bigrams"""
        words = text.split()
        tokens = list(words)
        if self.ngram_range[1] >= 2 and len(words) > 1:
            for i in range(len(words) - 1):
                tokens.append(f"{words[i]} {words[i+1]}")
        return tokens

    def _fuzzy_match(self, cleaned_text: str) -> Tuple[Optional[str], float]:
        """
        مطابقة تقريبية بمسافة ليفنشتاين تتسامح مع الأخطاء الإملائية والتشويش الصوتي
        """
        words = cleaned_text.split()
        best_intent = None
        best_score = 0.0

        # مرتكزات دلالية سريعة ومميزة للتعرف الفوري والتعامل مع أخطاء نطق الميكروفون في السيارة
        intent_anchors = {
            "weather_skill": ["طقس", "الطقس", "جو", "الجو", "حراره", "الحراره", "مطر", "امطار", "رياح", "مناخ"],
            "stop_skill": ["توقف", "اسكت", "اخرس", "الغاء", "صمت", "كفى", "قف", "صامت", "انهاء"],
            "time_date_skill": ["ساعه", "الساعه", "وقت", "الوقت", "تاريخ"],
            "greeting_skill": ["مرحبا", "سلام", "السلام", "صباح الخير", "مساء الخير", "اهلا", "تحياتي"],
            "assistant_info_skill": ["من انت", "اسمك", "عن نفسك", "قدراتك", "وظيفتك"]
        }

        for intent, anchors in intent_anchors.items():
            for anchor in anchors:
                norm_a = self.normalize_arabic(anchor)
                if f" {norm_a} " in f" {cleaned_text} ":
                    return intent, 0.95
                for w in words:
                    if len(w) >= 3 and len(norm_a) >= 3 and abs(len(w) - len(norm_a)) <= 1:
                        if levenshtein_similarity(w, norm_a) >= 0.75:
                            return intent, 0.92

        # 2. مطابقة كامل العبارة مع الأنماط المخزنة
        for intent, patterns in self.intent_patterns.items():
            for pat in patterns:
                sim = levenshtein_similarity(cleaned_text, pat)
                if sim > best_score:
                    best_score = sim
                    best_intent = intent

        return best_intent, best_score

    def parse_intent(self, utterance: str, context: Optional[Any] = None) -> Dict[str, Any]:
        """
        تحليل العبارة المنطوقة واستخراج النية الأكثر احتمالاً مع درجة الثقة،
        مع مراعاة سياق الحوار السابق (FSM Context)
        """
        if utterance and len(utterance) > 256:
            utterance = utterance[:256]
        cleaned = self.normalize_arabic(utterance)
        if not cleaned:
            return {
                "intent": "fallback_skill",
                "confidence": 0.0,
                "utterance": utterance,
                "cleaned": ""
            }

        # 1. فحص السياق السابق (Follow-up Turn Resolution)
        if context and hasattr(context, "last_intent") and context.last_intent:
            words = cleaned.split()
            # إذا كانت الجملة تبدأ بحرف عطف استكمالي أو ظرف زمني استكمالي قصير مثل ("وغداً؟"، "وفي دبي؟"، "ماذا عن القاهرة؟")
            is_followup = (
                len(words) <= 3 and (
                    cleaned.startswith("و") or
                    any(w in ("غدا", "بعده", "امس") for w in words) or
                    "ماذا عن" in cleaned
                )
            )
            # التأكد من أنها ليست جملة استفهامية جديدة أو أمراً مستقلاً (مثل: كيف، ما، هل، احسب، توقف، مرحبا، صف)
            independent_commands = {"احسب", "توقف", "اسكت", "مرحبا", "صف", "عرف", "اشرح", "الف", "كم", "من", "كيف", "ما", "هل"}
            if is_followup and not any(w in independent_commands for w in words):
                return {
                    "intent": context.last_intent,
                    "confidence": 0.95,
                    "utterance": utterance,
                    "cleaned": cleaned,
                    "match_type": "contextual_followup"
                }

        # 2. المطابقة التقريبية عبر ليفنشتاين
        fuzzy_intent, fuzzy_score = self._fuzzy_match(cleaned)
        if fuzzy_score >= 0.80 and fuzzy_intent:
            return {
                "intent": fuzzy_intent,
                "confidence": round(fuzzy_score, 4),
                "utterance": utterance,
                "cleaned": cleaned,
                "match_type": "fuzzy_levenshtein"
            }

        # 3. مصنف TF-IDF
        if not self.is_loaded:
            if fuzzy_intent and fuzzy_score >= 0.60:
                return {
                    "intent": fuzzy_intent,
                    "confidence": round(fuzzy_score, 4),
                    "utterance": utterance,
                    "cleaned": cleaned,
                    "match_type": "fuzzy_levenshtein"
                }
            return {
                "intent": "general_knowledge_skill",
                "confidence": 0.5,
                "utterance": utterance,
                "cleaned": cleaned,
                "match_type": "default_unloaded"
            }

        tokens = self._tokenize(cleaned)
        counts: Dict[str, int] = {}
        for t in tokens:
            if t in self.vocab:
                counts[t] = counts.get(t, 0) + 1

        if not counts:
            if fuzzy_intent and fuzzy_score >= 0.55:
                return {
                    "intent": fuzzy_intent,
                    "confidence": round(fuzzy_score, 4),
                    "utterance": utterance,
                    "cleaned": cleaned,
                    "match_type": "fuzzy_levenshtein"
                }
            return {
                "intent": "fallback_skill",
                "confidence": 0.2,
                "utterance": utterance,
                "cleaned": cleaned,
                "match_type": "out_of_vocab"
            }

        vec = [0.0] * len(self.vocab)
        for term, cnt in counts.items():
            idx = self.vocab[term]
            tf = (1.0 + math.log(cnt)) if self.sublinear_tf else float(cnt)
            vec[idx] = tf * self.idf[idx]

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]

        logits = []
        for c_idx in range(len(self.classes)):
            score = self.bias[c_idx]
            c_weights = self.weights[c_idx]
            for term in counts:
                idx = self.vocab[term]
                score += c_weights[idx] * vec[idx]
            logits.append(score)

        max_logit = max(logits)
        exp_scores = [math.exp(l - max_logit) for l in logits]
        total_exp = sum(exp_scores)
        probabilities = [s / total_exp for s in exp_scores]

        best_idx = probabilities.index(max(probabilities))
        best_intent = self.classes[best_idx]
        best_conf = probabilities[best_idx]

        # تعزيز النتيجة بنسبة المطابقة التقريبية إذا توافقتا
        if fuzzy_intent and fuzzy_intent == best_intent:
            best_conf = min(0.99, max(best_conf, fuzzy_score * 0.95))
        elif fuzzy_intent and fuzzy_score >= 0.75 and best_conf < 0.60:
            best_intent = fuzzy_intent
            best_conf = fuzzy_score

        return {
            "intent": best_intent,
            "confidence": round(best_conf, 4),
            "utterance": utterance,
            "cleaned": cleaned,
            "match_type": "hybrid_tfidf_fuzzy"
        }
