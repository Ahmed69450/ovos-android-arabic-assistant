# -*- coding: utf-8 -*-
"""
أداة تنقية وتجريد النصوص الصارمة للمساعد الصوتي OVOS Android.
تستخدم لتنظيف النصوص قبل إرسالها إلى واجهة المستخدم (UI) ومحرك تحويل النص إلى كلام (TTS).
"""

import html
import re


class TextSanitizer:
    """أداة تنقية وتجريد النصوص من الماركداون والوسوم والروابط والرموز التعبيرية والأسطر الجديدة"""

    URL_PATTERN = re.compile(r'https?://\S+|www\.\S+')
    HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
    MARKDOWN_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\([^\)]+\)')
    MARKDOWN_FORMAT_PATTERN = re.compile(r'[*_~`#>]')
    EMOJI_PATTERN = re.compile(
        r'[\U00010000-\U0010FFFF]'
        r'|[\u2600-\u26FF]'
        r'|[\u2700-\u27BF]'
        r'|[\u2300-\u23FF]'
        r'|[\u2B00-\u2BFF]'
        r'|[\u2190-\u21FF]'
        r'|[\uFE00-\uFE0F]'
        r'|[\u200D]'
        r'|[\u20E3]'
    )
    SPEECH_PUNCT_PATTERN = re.compile(r'["\'\(\)\{\}\[\]«»“”‘’]')
    PUNCT_SPACING_PATTERN = re.compile(r'\s+([!?.,:;؟،؛])')

    @classmethod
    def sanitize(cls, text: str) -> str:
        """
        تنقية النص بالكامل لواجهة المستخدم والصوت:
        - فك تشفير كيانات HTML (&amp; -> & إلخ)
        - تحويل روابط الماركداون [anchor](url) إلى نص الرابط فقط
        - إزالة الروابط المباشرة (http://, https://, www.)
        - إزالة وسوم HTML (<p>, <b>, </a> إلخ)
        - إزالة رموز تنسيق الماركداون (**, *, __, _, ~, `, #, >)
        - إزالة الرموز التعبيرية (Emojis)
        - استبدال محارف السطور الجديدة والمسافات البادئة (\n, \r, \t) بمسافة واحدة
        - دمج المسافات المتكررة وإزالة المسافات الزائدة قبل علامات الترقيم
        """
        if not text or not isinstance(text, str):
            return ""

        # 1. Unescape HTML entities
        text = html.unescape(text)

        # 2. Extract markdown link anchor text
        text = cls.MARKDOWN_LINK_PATTERN.sub(r'\1', text)

        # 3. Strip URLs
        text = cls.URL_PATTERN.sub(' ', text)

        # 4. Strip HTML tags
        text = cls.HTML_TAG_PATTERN.sub(' ', text)

        # 5. Strip Markdown formatting symbols
        text = cls.MARKDOWN_FORMAT_PATTERN.sub(' ', text)

        # 6. Strip Emojis
        text = cls.EMOJI_PATTERN.sub('', text)

        # 7. Replace all newlines and tabs with single space
        text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')

        # 8. Collapse consecutive spaces
        text = re.sub(r'\s+', ' ', text).strip()

        # 9. Clean up spacing before punctuation
        text = cls.PUNCT_SPACING_PATTERN.sub(r'\1', text)

        return text.strip()

    @classmethod
    def clean_for_speech(cls, text: str) -> str:
        """
        تنقية النص لمحرك النطق الصوتي (TTS):
        تطبق تنقية sanitize() بالإضافة إلى إزالة علامات الاقتباس والأقواس
        التي قد تسبب نطقاً غير طبيعي أو توقفات غير مرغوبة.
        """
        cleaned = cls.sanitize(text)
        if not cleaned:
            return ""

        # Remove quotes and brackets
        cleaned = cls.SPEECH_PUNCT_PATTERN.sub(' ', cleaned)

        # Collapse spaces and clean up punctuation spacing
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        cleaned = cls.PUNCT_SPACING_PATTERN.sub(r'\1', cleaned)

        return cleaned.strip()
