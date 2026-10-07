# -*- coding: utf-8 -*-
"""
محرك الفهم اللغوي الطبيعي (NLU) للغة العربية الخفيف والداعم للاستدلال المحلي في أندرويد
يستند إلى استخراج الخصائص TF-IDF ومصنف خفيف الوزن يعمل بأعلى سرعة دون اتصال بالإنترنت
"""

import os
import re
import json
import math
from typing import Dict, Any, List, Optional, Tuple

class ArabicNLUEngine:
    """محرك NLU المحلي المستوحى من معمارية OVOS لمعالجة وفهم النصوص المنطوقة باللغة العربية"""

    def __init__(self, weights_source: Optional[Any] = None):
        self.vocab: Dict[str, int] = {}
        self.idf: List[float] = []
        self.classes: List[str] = []
        self.weights: List[List[float]] = []
        self.bias: List[float] = []
        self.ngram_range: Tuple[int, int] = (1, 2)
        self.sublinear_tf: bool = True
        self.is_loaded: bool = False

        # معالجات فورية سريعة للأوامر الحيوية ذات الأولوية القصوى (مثل OVOS Padatious/Stop Service)
        self._fast_rules = {
            "stop_skill": ["توقف", "اسكت", "الغاء", "اخرس", "انهاء", "توقف عن الكلام", "اغلق", "كفى", "صمت", "قف"],
            "greeting_skill": ["مرحبا", "السلام عليكم", "صباح الخير", "مساء الخير", "اهلا وسهلا", "كيف حالك", "شو اخبارك"],
            "time_date_skill": ["كم الساعه", "ما هو الوقت", "الوقت الان", "تاريخ اليوم", "اي يوم نحن"],
            "assistant_info_skill": ["من انت", "ما اسمك", "عرف عن نفسك", "ما هي قدراتك", "ماذا تفعل"]
        }

        if weights_source:
            self.load_model(weights_source)

    @staticmethod
    def normalize_arabic(text: str) -> str:
        """معالجة وتوحيد الأحرف العربية وإزالة التشكيل والكشيدة لضمان دقة المطابقة"""
        if not isinstance(text, str):
            return ""
        # إزالة التشكيل والحركات
        text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
        # إزالة التطويل
        text = re.sub(r'\u0640', '', text)
        # توحيد الألف
        text = re.sub(r'[إأآا]', 'ا', text)
        # توحيد الياء
        text = re.sub(r'[يى]', 'ي', text)
        # توحيد التاء المربوطة
        text = re.sub(r'ة', 'ه', text)
        # إزالة علامات الترقيم والأرقام غير المرغوبة
        text = re.sub(r'[^\w\s]', ' ', text)
        # توحيد المسافات
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def load_model(self, source: Any) -> None:
        """تحميل أوزان النموذج من ملف JSON أو مسار أو كائن قاموس"""
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
        """تفكيك الجملة إلى كلمات وتراكيب ثنائية (Unigrams & Bigrams)"""
        words = text.split()
        tokens = list(words)
        if self.ngram_range[1] >= 2 and len(words) > 1:
            for i in range(len(words) - 1):
                tokens.append(f"{words[i]} {words[i+1]}")
        return tokens

    def _check_fast_rules(self, normalized_text: str) -> Optional[Tuple[str, float]]:
        """التحقق من القواعد المباشرة ذات الأولوية العالية المشابهة لـ OVOS Matcher"""
        for intent_tag, patterns in self._fast_rules.items():
            for pat in patterns:
                norm_pat = self.normalize_arabic(pat)
                if norm_pat in normalized_text or normalized_text in norm_pat:
                    return intent_tag, 0.99
        return None

    def parse_intent(self, utterance: str) -> Dict[str, Any]:
        """
        تحليل العبارة المنطوقة واستخراج النية الأكثر احتمالاً مع درجة الثقة
        """
        cleaned = self.normalize_arabic(utterance)
        if not cleaned:
            return {
                "intent": "fallback_skill",
                "confidence": 0.0,
                "utterance": utterance,
                "cleaned": ""
            }

        # 1. التدقيق السريع للقواعد ذات الأولوية القصوى
        fast_match = self._check_fast_rules(cleaned)
        if fast_match:
            intent, conf = fast_match
            return {
                "intent": intent,
                "confidence": conf,
                "utterance": utterance,
                "cleaned": cleaned,
                "match_type": "fast_rule"
            }

        if not self.is_loaded:
            return {
                "intent": "general_knowledge_skill",
                "confidence": 0.5,
                "utterance": utterance,
                "cleaned": cleaned,
                "match_type": "default_unloaded"
            }

        # 2. حساب مصفوفة TF-IDF للنص المدخل
        tokens = self._tokenize(cleaned)
        counts: Dict[str, int] = {}
        for t in tokens:
            if t in self.vocab:
                counts[t] = counts.get(t, 0) + 1

        if not counts:
            return {
                "intent": "general_knowledge_skill",
                "confidence": 0.2,
                "utterance": utterance,
                "cleaned": cleaned,
                "match_type": "out_of_vocab"
            }

        # تكوين المتجه
        vec = [0.0] * len(self.vocab)
        for term, cnt in counts.items():
            idx = self.vocab[term]
            tf = (1.0 + math.log(cnt)) if self.sublinear_tf else float(cnt)
            vec[idx] = tf * self.idf[idx]

        # تسوية المتجه L2 Norm
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]

        # 3. حساب درجات المصنف (Logits)
        logits = []
        for c_idx in range(len(self.classes)):
            score = self.bias[c_idx]
            c_weights = self.weights[c_idx]
            # ضرب نقطي سريع للعناصر الموجودة فقط
            for term in counts:
                idx = self.vocab[term]
                score += c_weights[idx] * vec[idx]
            logits.append(score)

        # 4. حساب دالة الاحتمال Softmax
        max_logit = max(logits)
        exp_scores = [math.exp(l - max_logit) for l in logits]
        total_exp = sum(exp_scores)
        probabilities = [s / total_exp for s in exp_scores]

        best_idx = probabilities.index(max(probabilities))
        best_intent = self.classes[best_idx]
        best_conf = probabilities[best_idx]

        return {
            "intent": best_intent,
            "confidence": round(best_conf, 4),
            "utterance": utterance,
            "cleaned": cleaned,
            "match_type": "tfidf_classifier"
        }
