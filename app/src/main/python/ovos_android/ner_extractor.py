# -*- coding: utf-8 -*-
"""Arabic Named Entity Recognition (NER) and Slot Extractor.

Extracts locations (cities), temporal dates/times, and numbers from Arabic
utterances without external C-extension dependencies. Uses gazetteers and
Levenshtein similarity for fast offline inference (<2ms).
"""

import re
from typing import Dict, Any, Optional, List, Tuple


def levenshtein_similarity(s1: str, s2: str) -> float:
    """Calculate normalized Levenshtein similarity between two strings.

    Returns a float in [0.0, 1.0], where 1.0 is an exact match and 0.0 means
    no similarity or at least one empty string.
    """
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0

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


class ArabicNERExtractor:
    """Fast, lightweight Arabic Named Entity Recognition (NER) & Slot Extractor.

    Designed for embedded and offline Android environments with < 2ms latency.
    """

    CITIES_GAZETTEER: Dict[str, List[str]] = {
        "الرياض": ["الرياض", "رياض"],
        "جدة": ["جدة", "جده"],
        "مكة": ["مكة المكرمة", "مكه المكرمه", "مكة", "مكه"],
        "المدينة المنورة": ["المدينة المنورة", "المدينه المنوره", "المدينة", "المدينه"],
        "الدمام": ["الدمام", "دمام"],
        "الخبر": ["الخبر", "خبر"],
        "الطائف": ["الطائف", "طائف"],
        "تبوك": ["تبوك"],
        "أبها": ["أبها", "ابها"],
        "القاهرة": ["القاهرة", "القاهره", "قاهرة", "قاهره", "مصر"],
        "الإسكندرية": ["الإسكندرية", "الاسكندرية", "الاسكندريه", "اسكندرية", "اسكندريه"],
        "الجيزة": ["الجيزة", "الجيزه", "جيزة", "جيزه"],
        "دبي": ["دبي", "دبى"],
        "أبوظبي": ["أبوظبي", "ابوظبي", "أبو ظبي", "ابو ظبي"],
        "الشارقة": ["الشارقة", "الشارقه", "شارقة", "شارقه"],
        "الدوحة": ["الدوحة", "الدوحه", "دوحة", "دوحه", "قطر"],
        "الكويت": ["الكويت", "كويت"],
        "المنامة": ["المنامة", "المنامه", "منامة", "منامه", "بحرين", "البحرين"],
        "مسقط": ["مسقط", "سلطنة عمان"],
        "عمان": ["عمان", "عمّان", "الاردن", "الأردن"],
        "بيروت": ["بيروت", "لبنان"],
        "بغداد": ["بغداد", "العراق"],
        "دمشق": ["دمشق", "سوريا", "الشام"],
        "القدس": ["القدس", "فلسطين"],
        "طرابلس": ["طرابلس", "ليبيا"],
        "تونس": ["تونس"],
        "الجزائر": ["الجزائر"],
        "الرباط": ["الرباط", "المغرب"],
        "الدار البيضاء": ["الدار البيضاء", "الدار البيضا", "كازابلانكا", "كازا"],
        "صنعاء": ["صنعاء", "اليمن"],
        "الخرطوم": ["الخرطوم", "السودان"]
    }

    DATE_PATTERNS: Dict[str, List[str]] = {
        "بعد غد": ["بعد غد", "بعد غدا", "بعد بكرة", "بعد بكره"],
        "الأسبوع القادم": ["الاسبوع القادم", "الأسبوع القادم", "الاسبوع الجاي", "الاسبوع المقبل", "الأسبوع المقبل"],
        "اليوم": ["اليوم", "هذا اليوم", "الآن", "الان"],
        "غداً": ["غدا", "غداً", "بكرة", "باكر", "بكره"],
        "أمس": ["امس", "أمس", "البارحة", "البارحه"]
    }

    ARABIC_INDIC_DIGITS = {
        '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
        '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
    }

    def __init__(self) -> None:
        # Pre-build fast exact lookup maps for cities and dates
        self._city_lookup: Dict[str, str] = {}
        for std_city, variations in self.CITIES_GAZETTEER.items():
            for var in variations:
                norm_v = self._normalize(var)
                if norm_v:
                    self._city_lookup[norm_v] = std_city

        self._normalized_city_variations: List[Tuple[str, str]] = list(self._city_lookup.items())

        self._date_lookup: Dict[str, str] = {}
        for std_date, variations in self.DATE_PATTERNS.items():
            for var in variations:
                norm_v = self._normalize(var)
                if norm_v:
                    self._date_lookup[norm_v] = std_date

    @staticmethod
    def _normalize(text: Optional[str]) -> str:
        """Normalize Arabic text by removing tashkeel, standardizing letters, and punctuation."""
        if not text:
            return ""
        # Remove Tashkeel (harakat) and Tatweel
        text = re.sub(r'[\u064B-\u065F\u0670\u0640]', '', text)
        # Normalize Alef forms
        text = re.sub(r'[إأآا]', 'ا', text)
        # Normalize Yaa and Alef Maqsura
        text = re.sub(r'[يى]', 'ي', text)
        # Normalize Taa Marbuta to Haa
        text = re.sub(r'ة', 'ه', text)
        # Replace punctuation and symbols with whitespace
        text = re.sub(r'[^\w\s]', ' ', text)
        # Normalize whitespace
        return ' '.join(text.split())

    def extract_slots(self, utterance: Optional[str]) -> Dict[str, Any]:
        """Extract locations, dates, and numbers from an Arabic utterance."""
        slots: Dict[str, Any] = {}
        if not utterance or not isinstance(utterance, str):
            return slots

        norm_utt = self._normalize(utterance)
        if not norm_utt:
            return slots

        words = norm_utt.split()
        num_words = len(words)

        # 1. Location Extraction (Exact via n-grams: 3-grams down to 1-grams)
        matched_city: Optional[str] = None
        for n in (3, 2, 1):
            for i in range(num_words - n + 1):
                gram = ' '.join(words[i:i + n])
                if gram in self._city_lookup:
                    matched_city = self._city_lookup[gram]
                    break
                # Handle single-word prepositions (بـ, لـ, فـ, وـ, للـ)
                if n == 1 and len(gram) > 3:
                    if gram[0] in ('ب', 'ل', 'ف', 'و') and gram[1:] in self._city_lookup:
                        matched_city = self._city_lookup[gram[1:]]
                        break
                    elif gram.startswith('لل') and ('ال' + gram[2:]) in self._city_lookup:
                        matched_city = self._city_lookup['ال' + gram[2:]]
                        break
            if matched_city:
                break

        if matched_city:
            slots["location"] = matched_city
        else:
            # Fuzzy Location fallback if no direct match found
            best_city: Optional[str] = None
            best_sim = 0.0

            for word in words:
                lw = len(word)
                if lw < 3:
                    continue
                for norm_var, std_city in self._normalized_city_variations:
                    lv = len(norm_var)
                    # Length difference pruning for performance
                    if abs(lw - lv) > 2:
                        continue
                    sim = levenshtein_similarity(word, norm_var)
                    if sim > best_sim and sim >= 0.75:
                        best_sim = sim
                        best_city = std_city

            if best_city:
                slots["location"] = best_city

        # 2. Date / Time Extraction (Exact via n-grams: 3-grams down to 1-grams)
        matched_date: Optional[str] = None
        for n in (3, 2, 1):
            for i in range(num_words - n + 1):
                gram = ' '.join(words[i:i + n])
                if gram in self._date_lookup:
                    matched_date = self._date_lookup[gram]
                    break
            if matched_date:
                break

        if matched_date:
            slots["date"] = matched_date

        # 3. Number Extraction (Supports ASCII and Arabic-Indic digits)
        num_str = utterance
        for ar_d, en_d in self.ARABIC_INDIC_DIGITS.items():
            num_str = num_str.replace(ar_d, en_d)

        num_match = re.search(r'\b\d+\b', num_str)
        if num_match:
            try:
                slots["number"] = int(num_match.group(0))
            except ValueError:
                pass

        return slots
