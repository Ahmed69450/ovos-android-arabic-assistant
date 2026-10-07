# -*- coding: utf-8 -*-
"""
فحص واختبار شامل لمحرك OVOS المعدل للأندرويد عبر الجسر البرمجي
"""

import sys
import os
import io
import json

# إضافة مسار python للـ sys.path
sys.path.insert(0, os.path.abspath("app/src/main/python"))

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import ovos_bridge

model_path = os.path.abspath("app/src/main/assets/model_weights.json")
intents_path = os.path.abspath("app/src/main/assets/intents.json")

print("1. تهيئة النظام عبر ovos_bridge.initialize...")
init_success = ovos_bridge.initialize(model_path, intents_path)
print(f"نتيجة التهيئة: {init_success}")

skills_json = ovos_bridge.get_registered_skills()
print(f"المهارات المسجلة: {skills_json}")

test_queries = [
    "مرحبا كيف حالك يا صديقي",
    "عرفني بنفسك وما وظيفتك",
    "كم الساعة الآن وما تاريخ اليوم",
    "ما هي عاصمة فرنسا",
    "أعطني نصائح للبقاء بصحة جيدة",
    "صف بنية الذرة",
    "احسب 15 * 4",
    "ألف قصة قصيرة عن طفل يحب النجوم",
    "كيف الطقس اليوم",
    "توقف عن الحديث واسكت"
]

print("\n--- 2. اختبار تفاعل المساعد الصوتي مع الأوامر باللغة العربية ---")
for q in test_queries:
    resp_json = ovos_bridge.process_utterance(q)
    data = json.loads(resp_json)
    print(f"\n[المستخدم]: {q}")
    print(f"  -> النية المطابقة: {data['intent']} (الثقة: {data['confidence'] * 100:.1f}%)")
    print(f"  -> رد المساعد: {data['response']}")
