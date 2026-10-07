# -*- coding: utf-8 -*-
import unittest
import sys
import os
import time

sys.path.insert(0, os.path.abspath("app/src/main/python"))
from ovos_android.ner_extractor import ArabicNERExtractor, levenshtein_similarity


class TestArabicNERExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = ArabicNERExtractor()

    def test_levenshtein_similarity(self):
        self.assertAlmostEqual(levenshtein_similarity("", ""), 0.0)
        self.assertAlmostEqual(levenshtein_similarity("الرياض", ""), 0.0)
        self.assertAlmostEqual(levenshtein_similarity("الرياض", "الرياض"), 1.0)
        self.assertGreater(levenshtein_similarity("اسكندريه", "اسكندرية"), 0.8)
        self.assertLess(levenshtein_similarity("الرياض", "القاهرة"), 0.5)

    def test_extract_location_exact(self):
        slots = self.extractor.extract_slots("ما هي حالة الطقس في الرياض")
        self.assertEqual(slots.get("location"), "الرياض")

        slots_jeddah = self.extractor.extract_slots("الطقس في جده")
        self.assertEqual(slots_jeddah.get("location"), "جدة")

        slots_cairo = self.extractor.extract_slots("درجة الحرارة في القاهرة")
        self.assertEqual(slots_cairo.get("location"), "القاهرة")

    def test_extract_location_fuzzy(self):
        slots = self.extractor.extract_slots("كيف الجو في اسكندريه اليوم")
        self.assertEqual(slots.get("location"), "الإسكندرية")
        self.assertEqual(slots.get("date"), "اليوم")

        slots_dubai = self.extractor.extract_slots("هل الجو حار في دبى")
        self.assertEqual(slots_dubai.get("location"), "دبي")

        slots_abudhabi = self.extractor.extract_slots("الطقس في ابوظبي")
        self.assertEqual(slots_abudhabi.get("location"), "أبوظبي")

        # Typo: extra letter "الريياض"
        slots_typo = self.extractor.extract_slots("الطقس في الريياض")
        self.assertEqual(slots_typo.get("location"), "الرياض")

    def test_extract_date_relative(self):
        slots = self.extractor.extract_slots("هل ستمطر غدا في دبي")
        self.assertEqual(slots.get("location"), "دبي")
        self.assertEqual(slots.get("date"), "غداً")

        # "بعد غد" must not be truncated or misidentified as "غداً"
        slots_after = self.extractor.extract_slots("ما هو الطقس بعد غد")
        self.assertEqual(slots_after.get("date"), "بعد غد")

        slots_yesterday = self.extractor.extract_slots("كيف كان الجو امس")
        self.assertEqual(slots_yesterday.get("date"), "أمس")

        slots_next_week = self.extractor.extract_slots("حالة الطقس الاسبوع القادم في عمان")
        self.assertEqual(slots_next_week.get("location"), "عمان")
        self.assertEqual(slots_next_week.get("date"), "الأسبوع القادم")

    def test_extract_numbers(self):
        slots = self.extractor.extract_slots("اضبط المكيف على 22 درجة")
        self.assertEqual(slots.get("number"), 22)

        slots_temp = self.extractor.extract_slots("درجة الحرارة 35")
        self.assertEqual(slots_temp.get("number"), 35)

        # Arabic-Indic digits
        slots_arabic_digits = self.extractor.extract_slots("اضبط المنبه على ٥ دقائق")
        self.assertEqual(slots_arabic_digits.get("number"), 5)

    def test_empty_and_irrelevant_utterances(self):
        self.assertEqual(self.extractor.extract_slots(""), {})
        self.assertEqual(self.extractor.extract_slots(None), {})
        self.assertEqual(self.extractor.extract_slots("مرحبا كيف حالك"), {})
        # Should not falsely match "رياض" inside "رياضيات"
        slots_math = self.extractor.extract_slots("ما هي مسائل الرياضيات")
        self.assertNotIn("location", slots_math)

    def test_performance_under_2ms(self):
        sample_utterances = [
            "ما هي حالة الطقس في الرياض اليوم",
            "كيف الجو في اسكندريه غدا",
            "درجة الحرارة في دبى",
            "اضبط المكيف على 24 درجة بعد غد",
            "هل ستمطر في الريياض الاسبوع القادم",
        ]
        start_time = time.perf_counter()
        iterations = 200
        for _ in range(iterations):
            for utt in sample_utterances:
                self.extractor.extract_slots(utt)
        total_time = time.perf_counter() - start_time
        avg_time_per_query = total_time / (iterations * len(sample_utterances))
        # Brief requirement: < 2ms (0.002s) per query
        self.assertLess(avg_time_per_query, 0.002, f"Average query time {avg_time_per_query*1000:.2f}ms exceeds 2ms")


if __name__ == "__main__":
    unittest.main()
