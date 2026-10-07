# -*- coding: utf-8 -*-
"""
جسر أندرويد لـ OpenVoiceOS (OVOS Android Bridge)
يوفر واجهة برمجية موحدة تُستدعى مباشرة من كود Kotlin عبر Chaquopy
"""

import os
import sys
import json
from typing import Optional

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from ovos_android.skill_router import SkillRouter

_router_instance: Optional[SkillRouter] = None

def _safe_log(msg: str) -> None:
    try:
        print(msg)
    except Exception:
        try:
            sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
        except Exception:
            pass

def initialize(model_weights_path: str, intents_data_path: Optional[str] = None) -> bool:
    """
    تهيئة موجه مهارات OVOS من أندرويد
    :param model_weights_path: مسار ملف أوزان النموذج model_weights.json في أصول أندرويد
    :param intents_data_path: مسار ملف النوايا والبيانات intents.json
    :return: True عند نجاح التهيئة
    """
    global _router_instance
    try:
        _router_instance = SkillRouter(
            model_weights_path=model_weights_path,
            intents_data_path=intents_data_path
        )
        _safe_log("تمت تهيئة محرك OpenVoiceOS بنجاح في بيئة أندرويد!")
        return True
    except Exception as e:
        _safe_log(f"فشل في تهيئة محرك OVOS: {str(e)}")
        return False

def process_utterance(utterance_text: str) -> str:
    """
    معالجة النص المنطوق من المستخدم وإرجاع النتيجة بتنسيق JSON لكود Kotlin
    :param utterance_text: جملة المستخدم باللغة العربية
    :return: نص JSON يحتوي على response و intent و confidence و slots
    """
    global _router_instance
    if _router_instance is None:
        return json.dumps({
            "response": "عذراً، محرك المساعد الصوتي غير مهيأ بعد.",
            "intent": "none",
            "confidence": 0.0,
            "error": "Engine not initialized"
        }, ensure_ascii=False)

    try:
        result = _router_instance.process_utterance(utterance_text)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "response": "حدث خطأ داخلي أثناء معالجة الأمر الصوتي.",
            "intent": "error",
            "confidence": 0.0,
            "error": str(e)
        }, ensure_ascii=False)

def get_speech_response(utterance_text: str) -> str:
    """
    دالة مبسطة ترجع النص العربي مباشرة لنطقه عبر Android TextToSpeech
    """
    res_str = process_utterance(utterance_text)
    res_dict = json.loads(res_str)
    return res_dict.get("response", "")

def get_registered_skills() -> str:
    """استرجاع قائمة المهارات المسجلة في النظام"""
    global _router_instance
    if _router_instance is None:
        return "[]"
    skills_keys = list(_router_instance.skills.keys())
    return json.dumps(skills_keys, ensure_ascii=False)
