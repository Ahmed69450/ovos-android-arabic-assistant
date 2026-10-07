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
    
    # تعريف النوايا الأساسية لنظام المساعد الصوتي OVOS مع تنويع فائق في الصيغ واللهجات
    system_intents = {
        "greeting_skill": {
            "patterns": [
                "مرحبا", "السلام عليكم", "صباح الخير", "مساء الخير", 
                "اهلا وسهلا", "اهلا بك", "تحياتي", "كيف حالك", "شو اخبارك", 
                "مرحبا يا مساعد", "السلام عليكم ورحمة الله", "شلونك عيني",
                "شلونك يا غالي", "هلا والله", "هلا وغلا", "حياك الله", 
                "صباح النور", "مساء الورد", "كيف صحتك", "شخبارك اليوم", 
                "اهلين وسهلين", "مرحبا صديقي", "يومك سعيد", "سلامات"
            ],
            "responses": [
                "أهلاً وسهلاً بك! أنا مساعدك الصوتي الذكي، كيف يمكنني مساعدتك اليوم؟",
                "وعليكم السلام ورحمة الله وبركاته! يسعدني التحدث إليك في أي وقت.",
                "مرحباً بك! أتمنى أن تكون بأفضل حال وصحة، ما الذي تود معرفته؟",
                "أهلاً صديقي! أنا جاهز ومستعد للإجابة على أسئلتك وتنفيذ أوامرك."
            ]
        },
        "assistant_info_skill": {
            "patterns": [
                "من انت", "ما اسمك", "عرف عن نفسك", "ما هي قدراتك", 
                "ماذا تفعل", "ما وظيفتك", "من صنعك", "كيف تعمل", "هل انت ذكاء اصطناعي",
                "منو انت", "شنو اسمك", "شنو شغلك", "مين انت وشو بتعمل", "عرفني بيك",
                "عرف بحالك", "حدثني عن وظيفتك", "ما هي مميزاتك", "شنو تقدر تسوي",
                "شنو تكدر تساعدني", "هل انت روبوت", "من برمجك", "ما هو دورك"
            ],
            "responses": [
                "أنا مساعدك الصوتي الذكي المبني على معمارية OpenVoiceOS المخصصة لنظام أندرويد، أعمل محلياً بالكامل للحفاظ على خصوصيتك وسرعة استجابتك.",
                "اسمي المساعد الصوتي العربي، أساعدك في الإجابة على الأسئلة العامة، الحسابات، متابعة الطقس والوقت وتنظيم المهام دون الحاجة للاتصال بالسحابة.",
                "أنا نظام ذكاء اصطناعي صوتي محلي صُمم لخدمتك وفهم أوامرك باللغة العربية بسرعة فائقة وبدون أي استهلاك زائد للموارد."
            ]
        },
        "time_date_skill": {
            "patterns": [
                "كم الساعة", "ما هو الوقت الان", "اخبرني بالوقت", "الساعة كم", 
                "ما تاريخ اليوم", "اي يوم نحن", "ما التاريخ الهجري والميلادي", "تاريخ اليوم",
                "كم الساعة هسا", "الساعة كم الحين", "الوقت الحين", "شنو تاريخ اليوم",
                "كم التاريخ اليوم", "ايش اليوم والوقت", "اخبرني كم الوقت لو سمحت",
                "الساعة كم يا مساعد", "اي يوم في الاسبوع نحن", "تاريخ اليوم شنو"
            ],
            "responses": [
                "الوقت الحالي والتاريخ متاحان ومحدثان بدقة على جهازك.",
                "الساعة والتاريخ محددتان وفق توقيت جهازك المحلي."
            ]
        },
        "stop_skill": {
            "patterns": [
                "توقف", "اسكت", "الغاء", "اخرس", "انهاء", "توقف عن الكلام", "اغلق", "كفى",
                "كافي عاد اسكت", "بس خلاص الغي", "وقف حكي", "اصمت رجاء", "اسكت لو سمحت",
                "سد حلقك", "الغي كل شي", "انهاء المحادثة", "توقف عن الحديث", "لا تحجي بعد",
                "صامت", "اخرس وبس", "قف", "صمت"
            ],
            "responses": [
                "حسناً، توقفت عن الكلام. يمكنك مناداتي متى شئت.",
                "تم الإلغاء، أنا في وضع الاستعداد بانتظار أوامرك.",
                "إلى اللقاء، سأصمت الآن وتستطيع التحدث معي في أي لحظة."
            ]
        },
        "weather_skill": {
            "patterns": [
                "ما حالة الطقس", "كيف الجو اليوم", "هل ستمطر", "درجة الحرارة الان", 
                "توقعات الطقس غدا", "هل الجو بارد", "اخبرني بحالة الجو",
                "الجو شلونه اليوم", "شلون الجو برا", "بشرني عن الطقس", "هل فيه مطر اليوم",
                "الطقس في مدينتي", "كيف الطقس في الرياض", "هل الجو حار", "درجة الحرارة كم",
                "الجو غائم لو مشمس", "توقعات الامطار", "كيف مناخ اليوم", "حالة الطقس باجر",
                "الجو صحو ولا ممطر"
            ],
            "responses": [
                "يمكنني تزويدك بحالة الطقس ودرجات الحرارة وسرعة الرياح بدقة لأي مدينة تطلبها.",
                "الطقس معتدل ومناسب، ويمكنني إعطاؤك تفاصيل حالة الجو وتوقعات الأمطار فوراً."
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
        if any(k in norm for k in ['صحه', 'غذائ', 'طعام', 'تمرين', 'نوم', 'جسم', 'دواء', 'مرض', 'فيتامين', 'سعرات', 'رياضه', 'وزن', 'علاج', 'دايت', 'رجيم', 'لياقه', 'قلب', 'تنفس', 'مناعه', 'طبيب', 'الم', 'صداع', 'عضله', 'تغذيه']):
            return 'health_wellness_skill'
        elif any(k in norm for k in ['ذره', 'كيمياء', 'فيزياء', 'حاسوب', 'كمبيوتر', 'برمج', 'كود', 'بروتون', 'خليه', 'فضاء', 'كوكب', 'جين', 'الكترون', 'تقنيه', 'ذكاء اصطناعي', 'روبوت', 'هاتف', 'انترنت', 'شبك', 'نواه', 'طاقه', 'كهرباء', 'جاذبيه', 'خوارزميه']):
            return 'science_tech_skill'
        elif any(k in norm for k in ['عاصمه', 'تاريخ', 'دوله', 'حرب', 'معركه', 'قيصر', 'رئيس', 'نابليون', 'حضاره', 'قاره', 'نهر', 'مدينه', 'امبراطور', 'اين تقع', 'موقع', 'ملك', 'ثوره', 'محيط', 'بحر', 'جبل', 'بلاد']):
            return 'history_geography_skill'
        elif any(k in norm for k in ['احسب', 'حساب', 'رقم', 'معادله', 'كسر', 'رياضيات', 'هندسه', 'نسبه', 'ضرب', 'قسمه', 'طرح', 'جمع', 'حاصل', 'مساحه', 'محيط', 'زاويه', 'مثلث', 'جبر']):
            return 'math_logic_skill'
        elif any(k in norm for k in ['ترجم', 'مرادف', 'ضد', 'اعراب', 'نحو', 'صرف', 'معني كلمه', 'لغوي', 'مفرد', 'جمع كلمه', 'لغات', 'انجليزي']):
            return 'language_translation_skill'
        elif any(k in norm for k in ['قصه', 'روايه', 'قصيده', 'شعر', 'ابيات', 'تاليف', 'حكايه', 'سيناريو', 'خيال', 'مسرحيه']):
            return 'creative_writing_skill'
        elif any(k in norm for k in ['قائمه', 'خطوات', 'نصائح', 'اقتراح', 'خطه', 'جدول', 'تنظيم', 'روتين', 'اهداف', 'انتاجيه', 'مهام']):
            return 'daily_assistant_skill'
        else:
            return 'general_knowledge_skill'

    print("جاري تصنيف وتجهيز عينات مجموعة البيانات (14,000 سطر متوازن)...")
    category_limits = {
        "health_wellness_skill": 1800,
        "science_tech_skill": 1800,
        "history_geography_skill": 1600,
        "math_logic_skill": 1800,
        "creative_writing_skill": 1800,
        "daily_assistant_skill": 1800,
        "language_translation_skill": 900,
        "general_knowledge_skill": 2700
    }
    
    # زوج السؤال والجواب للاسترجاع المباشر
    qa_lookup = []
    
    for idx, row in df_clean.iterrows():
        inst = row['instruction']
        out = row['output']
        cat = classify(inst)
        limit = category_limits.get(cat, 1800)
        if len(intent_categories[cat]) < limit:
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
            "responses": intent_responses[tag][:25] # عينات استجابات افتراضية
        })
        
    dataset_structure = {
        "metadata": {
            "name": "Arabic OVOS Voice Assistant Intents - 14k Balanced",
            "version": "2.1.0",
            "language": "ar",
            "total_intents": len(final_intents),
            "total_patterns": sum(len(i["patterns"]) for i in final_intents)
        },
        "intents": final_intents,
        "qa_pairs": qa_lookup[:14200] # أزواج السؤال والإجابة المباشرة المرفقة
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
