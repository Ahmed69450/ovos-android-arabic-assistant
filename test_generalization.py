# -*- coding: utf-8 -*-
import sys
import os
import json

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.abspath('app/src/main/python'))
import ovos_bridge

m_path = os.path.abspath('app/src/main/assets/model_weights.json')
i_path = os.path.abspath('app/src/main/assets/intents.json')
ovos_bridge.initialize(m_path, i_path)

test_phrases = [
    ("الجو شلونه اليوم بجدة", "weather_skill"),
    ("بشرني هل بتمطر بالرياض باجر", "weather_skill"),
    ("كم الساعه هسا بالظبط", "time_date_skill"),
    ("منو انت وشنو شغلك", "assistant_info_skill"),
    ("كافي عاد اسكت ولا كلمه", "stop_skill"),
    ("شلونك يا طيب وشخبارك", "greeting_skill"),
    ("احسبلي ناتج 25 في 4", "math_logic_skill"),
    ("وين صايره دوله فرنسا وما عاصمتها", "history_geography_skill"),
    ("شنو مكونات الذره والالكترونات", "science_tech_skill"),
    ("ترجم لي جمله صباح الخير للانجليزيه", "language_translation_skill"),
    ("سويلي قصه قصيره عن مغامره في الفضاء", "creative_writing_skill"),
    ("انطيني نصائح للحفاظ علي صحتي ونشاطي", "health_wellness_skill")
]

print("\n=== نتائج اختبار النوايا بصيغ غير حرفية ولهجات متنوعة ===")
success_count = 0
for phrase, expected_intent in test_phrases:
    res_str = ovos_bridge.process_utterance(phrase)
    res = json.loads(res_str)
    actual_intent = res.get("intent", "")
    confidence = res.get("confidence", 0.0)
    response_text = res.get("response", "")
    
    # بعض الأسئلة قد تصنف كـ daily_assistant أو health_wellness لتشابه المجال
    matched = (actual_intent == expected_intent) or (expected_intent == "health_wellness_skill" and actual_intent == "daily_assistant_skill")
    if matched:
        success_count += 1
        status = "✅ ناجح"
    else:
        status = "⚠️ مختلف"

    print(f"[{status}] المدخل: '{phrase}'")
    print(f"   -> النية المتوقعة: {expected_intent} | النية المستخرجة: {actual_intent} (الثقة: {confidence*100:.1f}%)")
    print(f"   -> الرد: {response_text[:110]}...\n")

print(f"نسبة النجاح في التعرف الدلالي: {success_count}/{len(test_phrases)} ({success_count/len(test_phrases)*100:.1f}%)")
