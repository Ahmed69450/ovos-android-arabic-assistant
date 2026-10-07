# test_ner_extractor.py
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath("app/src/main/python"))
from ovos_android.ner_extractor import ArabicNERExtractor

class TestArabicNERExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = ArabicNERExtractor()

    def test_extract_location_exact(self):
        slots = self.extractor.extract_slots("ما هي حالة الطقس في الرياض")
        self.assertEqual(slots.get("location"), "الرياض")

    def test_extract_location_fuzzy(self):
        slots = self.extractor.extract_slots("كيف الجو في اسكندريه اليوم")
        self.assertEqual(slots.get("location"), "الإسكندرية")
        self.assertEqual(slots.get("date"), "اليوم")

    def test_extract_date_relative(self):
        slots = self.extractor.extract_slots("هل ستمطر غدا في دبي")
        self.assertEqual(slots.get("location"), "دبي")
        self.assertEqual(slots.get("date"), "غداً")

    def test_extract_compound_city(self):
        slots = self.extractor.extract_slots("كم درجة الحرارة في المدينة المنورة")
        self.assertEqual(slots.get("location"), "المدينة المنورة")

    def test_extract_prefixed_city(self):
        slots = self.extractor.extract_slots("الجو بالرياض كيف")
        self.assertEqual(slots.get("location"), "الرياض")

    def test_extract_numbers_arabic_indic(self):
        slots = self.extractor.extract_slots("اضبط المكيف على ٢٤ درجة")
        self.assertEqual(slots.get("number"), 24)

    def test_empty_and_none(self):
        self.assertEqual(self.extractor.extract_slots(""), {})
        self.assertEqual(self.extractor.extract_slots(None), {})

if __name__ == "__main__":
    unittest.main()
