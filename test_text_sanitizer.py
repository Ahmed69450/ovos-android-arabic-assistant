# -*- coding: utf-8 -*-
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath("app/src/main/python"))
from ovos_android.text_sanitizer import TextSanitizer


class TestTextSanitizer(unittest.TestCase):
    def test_strip_markdown(self):
        raw = "الطقس **مشمس** جداً و*دافئ* اليوم! انظر [هنا](https://weather.com)."
        clean = TextSanitizer.sanitize(raw)
        self.assertNotIn("**", clean)
        self.assertNotIn("*", clean)
        self.assertNotIn("https://", clean)
        self.assertNotIn("weather.com", clean)
        self.assertIn("هنا", clean)
        self.assertIn("الطقس مشمس جداً و دافئ اليوم! انظر هنا.", clean)

    def test_strip_markdown_headings_quotes_code(self):
        raw = "### عنوان رئيسي\n> اقتباس مهم\nاستخدم أمر `python main.py` الآن."
        clean = TextSanitizer.sanitize(raw)
        self.assertNotIn("###", clean)
        self.assertNotIn("#", clean)
        self.assertNotIn(">", clean)
        self.assertNotIn("`", clean)
        self.assertIn("عنوان رئيسي", clean)
        self.assertIn("اقتباس مهم", clean)
        self.assertIn("استخدم أمر python main.py الآن.", clean)

    def test_strip_html_and_newlines(self):
        raw = "<p>درجة الحرارة <b>25</b> &amp; معتدلة</p>\n\nغداً ماطر.\r\n"
        clean = TextSanitizer.sanitize(raw)
        self.assertNotIn("<p>", clean)
        self.assertNotIn("<b>", clean)
        self.assertNotIn("</p>", clean)
        self.assertNotIn("</b>", clean)
        self.assertNotIn("\n", clean)
        self.assertNotIn("\r", clean)
        self.assertIn("&", clean)
        self.assertEqual(clean, "درجة الحرارة 25 & معتدلة غداً ماطر.")

    def test_strip_emojis_and_extra_spaces(self):
        raw = "صباح الخير ☀️🚗!   كيف    حالك؟"
        clean = TextSanitizer.sanitize(raw)
        self.assertNotIn("☀️", clean)
        self.assertNotIn("🚗", clean)
        self.assertEqual(clean, "صباح الخير! كيف حالك؟")

    def test_strip_standalone_urls(self):
        raw = "تفضل بزيارة http://example.com/api أو www.google.com للمزيد."
        clean = TextSanitizer.sanitize(raw)
        self.assertNotIn("http://", clean)
        self.assertNotIn("www.google.com", clean)
        self.assertEqual(clean, "تفضل بزيارة أو للمزيد.")

    def test_clean_for_speech(self):
        raw = 'قال المساعد: "درجة الحرارة (25 مئوية) [معتدلة] {اليوم}".'
        speech = TextSanitizer.clean_for_speech(raw)
        self.assertNotIn('"', speech)
        self.assertNotIn("'", speech)
        self.assertNotIn("(", speech)
        self.assertNotIn(")", speech)
        self.assertNotIn("[", speech)
        self.assertNotIn("]", speech)
        self.assertNotIn("{", speech)
        self.assertNotIn("}", speech)
        self.assertEqual(speech, "قال المساعد: درجة الحرارة 25 مئوية معتدلة اليوم.")

    def test_all_markdown_symbols(self):
        raw = "__عريض__ و _مائل_ و ~مشطوب~ أو ~~مشطوب مرتين~~ مع # رأس و > اقتباس"
        clean = TextSanitizer.sanitize(raw)
        self.assertNotIn("_", clean)
        self.assertNotIn("~", clean)
        self.assertNotIn("#", clean)
        self.assertNotIn(">", clean)
        self.assertEqual(clean, "عريض و مائل و مشطوب أو مشطوب مرتين مع رأس و اقتباس")

    def test_newlines_tabs_carriage_returns(self):
        raw = "سطر 1\n\r\t  سطر 2\r\n\t  سطر 3\n"
        clean = TextSanitizer.sanitize(raw)
        self.assertEqual(clean, "سطر 1 سطر 2 سطر 3")

    def test_html_entities(self):
        raw = "العلم &amp; المعرفة &quot;مهمان&quot; &#39;جداً&#39;"
        clean = TextSanitizer.sanitize(raw)
        self.assertNotIn("&amp;", clean)
        self.assertNotIn("&quot;", clean)
        self.assertNotIn("&#39;", clean)
        self.assertEqual(clean, 'العلم & المعرفة "مهمان" \'جداً\'')

    def test_speech_quotes_and_brackets(self):
        raw = '«نص مقتبس» و "نص آخر" و \'مفرد\' و (أقواس) و [مربعة] و {معقوفة}'
        speech = TextSanitizer.clean_for_speech(raw)
        for char in ['«', '»', '"', "'", '(', ')', '[', ']', '{', '}']:
            self.assertNotIn(char, speech)
        self.assertEqual(speech, "نص مقتبس و نص آخر و مفرد و أقواس و مربعة و معقوفة")

    def test_empty_and_non_string_inputs(self):
        self.assertEqual(TextSanitizer.sanitize(""), "")
        self.assertEqual(TextSanitizer.sanitize(None), "")
        self.assertEqual(TextSanitizer.sanitize(123), "")
        self.assertEqual(TextSanitizer.clean_for_speech(""), "")
        self.assertEqual(TextSanitizer.clean_for_speech(None), "")


if __name__ == "__main__":
    unittest.main()
