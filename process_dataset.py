# -*- coding: utf-8 -*-
"""
معالجة مجموعة بيانات المحادثة العربية وتحويلها إلى intents.json متوافق مع معمارية OVOS
"""

import os
import sys
import io
import re
import json
import pandas as pd

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def normalize_arabic(text: str) -> str:
    """تنظيف وتوحيد الأحرف العربية لتحسين كفاءة التصنيف ومعالجة اللغات الطبيعية"""
    if not isinstance(text, str):
        return ""
    # إزالة التشكيل (الحركات)
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    # إزالة التطويل (الكشيدة)
    text = re.sub(r'\u0640', '', text)
    # توحيد أشكال الألف
    text = re.sub(r'[إأآا]', 'ا', text)
    # توحيد الياء والألف المقصورة
    text = re.sub(r'[يى]', 'ي', text)
    # توحيد التاء المربوطة والهاء
    text = re.sub(r'ة', 'ه', text)
    # إزالة الرموز والزوائد
    text = re.sub(r'[^\w\s]', ' ', text)
    # إزالة المسافات الزائدة
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def build_intents_json():
    parquet_path = r'C:\Users\Dell\.cache\kagglehub\datasets\omgits0mar\arabic-instruct-chatbot-dataset\versions\1\train-00000-of-00001-10520e8228c2c104.parquet'
    print(f"قراءة البيانات من: {parquet_path}")
    df = pd.read_parquet(parquet_path)
    
    # تنظيف البيانات
    df_clean = df[~df['output'].str.contains('<nooutput>', na=False)].dropna(subset=['instruction', 'output']).copy()
    df_clean['instruction'] = df_clean['instruction'].astype(str).str.strip()
    df_clean['output'] = df_clean['output'].astype(str).str.strip()
    df_clean = df_clean[(df_clean['instruction'].str.len() > 3) & (df_clean['output'].str.len() > 3)]
    
    # تعريف النوايا الأساسية لنظام المساعد الصوتي OVOS
    system_intents = {
        "greeting_skill": {
            "patterns": [
                "مرحبا", "السلام عليكم", "صباح الخير", "مساء الخير", 
                "اهلا وسهلا", "اهلا بك", "تحياتي", "كيف حالك", "شو اخبارك", 
                "مرحبا يا مساعد", "السلام عليكم ورحمة الله"
            ],
            "responses": [
                "أهلاً وسهلاً بك! أنا مساعدك الصوتي الذكي، كيف يمكنني مساعدتك؟",
                "وعليكم السلام ورحمة الله وبركاته! يسعدني التحدث إليك اليوم.",
                "مرحباً بك! أتمنى أن تكون بأفضل حال، ما الذي تود معرفته؟",
                "أهلاً! أنا هنا ومستعد لتنفيذ أوامرك والإجابة عن أسئلتك."
            ]
        },
        "assistant_info_skill": {
            "patterns": [
                "من انت", "ما اسمك", "عرف عن نفسك", "ما هي قدراتك", 
                "ماذا تفعل", "ما وظيفتك", "من صنعك", "كيف تعمل", "هل انت ذكاء اصطناعي"
            ],
            "responses": [
                "أنا مساعد صوتي محلي لنظام أندرويد مبني على بنية OpenVoiceOS وأعمل دون الحاجة للاتصال بالإنترنت.",
                "اسمي المساعد الصوتي العربي، تم تطويري باستخدام نواة OpenVoiceOS لمعالجة النوايا وتنفيذ المهارات محلياً.",
                "أنا نظام ذكي مصمم لمساعدتك في الإجابة عن الأسئلة، تنظيم المهام، وتقديم المعلومات بأعلى معايير الخصوصية وبدون سحابة."
            ]
        },
        "time_date_skill": {
            "patterns": [
                "كم الساعة", "ما هو الوقت الان", "اخبرني بالوقت", "الساعة كم", 
                "ما تاريخ اليوم", "اي يوم نحن", "ما التاريخ الهجري والميلادي", "تاريخ اليوم"
            ],
            "responses": [
                "الوقت الحالي محدد بدقة على هاتفك.",
                "تاريخ اليوم والوقت متاحان على شاشة جهازك."
            ]
        },
        "stop_skill": {
            "patterns": [
                "توقف", "اسكت", "الغاء", "اخرس", "انهاء", "توقف عن الكلام", "اغلق", "كفى"
            ],
            "responses": [
                "حسناً، توقفت.",
                "تم الإلغاء، أنا في وضع الاستعداد عندما تحتاجني.",
                "إلى اللقاء، يمكنك مناداتي في أي وقت."
            ]
        },
        "weather_skill": {
            "patterns": [
                "ما حالة الطقس", "كيف الجو اليوم", "هل ستمطر", "درجة الحرارة الان", 
                "توقعات الطقس غدا", "هل الجو بارد", "اخبرني بحالة الجو"
            ],
            "responses": [
                "حالة الطقس معتدلة، يمكنك تفقد تطبيق الطقس لمزيد من التفاصيل المحلية.",
                "الجو مناسب اليوم، تأكد من شرب كمية كافية من الماء."
            ]
        }
    }
    
    # تصنيف عينات Kaggle وتوزيعها على مهارات النوايا
    intent_categories = {
        "health_wellness_skill": [],
        "science_tech_skill": [],
        "history_geography_skill": [],
        "math_logic_skill": [],
        "language_translation_skill": [],
        "creative_writing_skill": [],
        "daily_assistant_skill": [],
        "general_knowledge_skill": []
    }
    
    intent_responses = {k: [] for k in intent_categories}
    
    def classify(t):
        norm = normalize_arabic(t)
        if any(k in norm for k in ['صحه', 'غذائ', 'طعام', 'تمرين', 'نوم', 'جسم', 'دواء', 'مرض', 'فيتامين', 'سعرات', 'رياضه', 'وزن', 'علاج']):
            return 'health_wellness_skill'
        elif any(k in norm for k in ['ذره', 'كيمياء', 'فيزياء', 'حاسوب', 'كمبيوتر', 'برمج', 'كود', 'بروتون', 'خليه', 'فضاء', 'كوكب', 'جين', 'الكترون', 'تقنيه', 'ذكاء اصطناعي']):
            return 'science_tech_skill'
        elif any(k in norm for k in ['عاصمه', 'تاريخ', 'دوله', 'حرب', 'معركه', 'قيصر', 'رئيس', 'نابليون', 'حضاره', 'قاره', 'نهر', 'مدينه', 'امبراطور']):
            return 'history_geography_skill'
        elif any(k in norm for k in ['احسب', 'حساب', 'رقم', 'معادله', 'كسر', 'رياضيات', 'هندسه', 'نسبه', 'ضرب', 'قسمه']):
            return 'math_logic_skill'
        elif any(k in norm for k in ['ترجم', 'مرادف', 'ضد', 'اعراب', 'نحو', 'صرف', 'معني كلمه', 'لغوي']):
            return 'language_translation_skill'
        elif any(k in norm for k in ['قصه', 'روايه', 'قصيده', 'شعر', 'ابيات', 'تاليف']):
            return 'creative_writing_skill'
        elif any(k in norm for k in ['قائمه', 'خطوات', 'نصائح', 'اقتراح', 'خطه', 'جدول']):
            return 'daily_assistant_skill'
        else:
            return 'general_knowledge_skill'

    print("جاري تصنيف وتجهيز عينات مجموعة البيانات...")
    # نأخذ عينات متوازنة من مجموعة البيانات
    # للحفاظ على ملف خفيف الوزن للأندرويد وسرعة الاستدلال، نأخذ حتى 800 نموذج لكل فئة
    max_per_category = 800
    
    # زوج السؤال والجواب للاسترجاع المباشر
    qa_lookup = []
    
    for idx, row in df_clean.iterrows():
        inst = row['instruction']
        out = row['output']
        cat = classify(inst)
        if len(intent_categories[cat]) < max_per_category:
            intent_categories[cat].append(inst)
            intent_responses[cat].append(out)
            qa_lookup.append({
                "instruction": inst,
                "response": out,
                "intent": cat
            })
            
    # تجميع ملف intents.json النهائي
    final_intents = []
    
    # 1. إضافة النوايا النظامية
    for tag, data in system_intents.items():
        final_intents.append({
            "tag": tag,
            "patterns": data["patterns"],
            "responses": data["responses"]
        })
        
    # 2. إضافة النوايا المعرفية والعملية المشتقة من البيانات
    for tag, patterns in intent_categories.items():
        final_intents.append({
            "tag": tag,
            "patterns": patterns,
            "responses": intent_responses[tag][:20] # عينات استجابات افتراضية
        })
        
    dataset_structure = {
        "metadata": {
            "name": "Arabic OVOS Voice Assistant Intents",
            "version": "1.0.0",
            "language": "ar",
            "total_intents": len(final_intents),
            "total_patterns": sum(len(i["patterns"]) for i in final_intents)
        },
        "intents": final_intents,
        "qa_pairs": qa_lookup[:3000] # أزواج السؤال والإجابة المباشرة المرفقة
    }
    
    # حفظ في مسار مساحة العمل
    with open("intents.json", "w", encoding="utf-8") as f:
        json.dump(dataset_structure, f, ensure_ascii=False, indent=2)
    print("تم حفظ intents.json بنجاح في مساحة العمل!")
    print(f"إجمالي النوايا: {len(final_intents)}")
    print(f"إجمالي الأنماط التدريبية: {sum(len(i['patterns']) for i in final_intents)}")
    
    # تجهيز مسار Android Assets وحفظ الملف به
    assets_dir = os.path.join("app", "src", "main", "assets")
    os.makedirs(assets_dir, exist_ok=True)
    with open(os.path.join(assets_dir, "intents.json"), "w", encoding="utf-8") as f:
        json.dump(dataset_structure, f, ensure_ascii=False, indent=2)
    print(f"تم نسخ ملف النوايا إلى: {assets_dir}/intents.json")

if __name__ == "__main__":
    build_intents_json()
