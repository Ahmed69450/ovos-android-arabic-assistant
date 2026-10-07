# -*- coding: utf-8 -*-
"""
برنامج تدريب نموذج الفهم اللغوي الطبيعي (NLU) العربي
المستوحى من معمارية OpenVoiceOS وتصديره بتنسيق خفيف الوزن إلى أصول تطبيق أندرويد
"""

import os
import sys
import io
import json
import re
import math
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def normalize_arabic(text: str) -> str:
    """تنظيف وتوحيد الحروف العربية وإزالة التشكيل والكشيدة"""
    if not isinstance(text, str):
        return ""
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    text = re.sub(r'\u0640', '', text)
    text = re.sub(r'[إأآا]', 'ا', text)
    text = re.sub(r'[يى]', 'ي', text)
    text = re.sub(r'ة', 'ه', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def train_and_export():
    intents_file = "intents.json"
    if not os.path.exists(intents_file):
        print(f"الملف {intents_file} غير موجود!")
        return

    print("جاري قراءة ملف النوايا intents.json...")
    with open(intents_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # إضافة أمثلة تعزيزية إضافية للنوايا الحوارية ونظام التحكم الصوتي لضمان حساسية عالية
    extra_patterns = {
        "greeting_skill": [
            "مرحبا", "مرحبا بك", "اهلا", "اهلا وسهلا", "السلام عليكم", "سلام عليكم",
            "صباح الخير", "مساء الخير", "تحياتي", "كيف حالك", "شو اخبارك", "كيفك",
            "هلا وغلا", "مرحبا يا مساعد", "السلام عليكم ورحمة الله", "صباح النور", "مساء النور",
            "يومك سعيد", "اهلا صديقي"
        ] * 25,
        "assistant_info_skill": [
            "من انت", "ما اسمك", "عرفني بنفسك", "ما هي قدراتك", "ماذا تفعل", 
            "ما وظيفتك", "من صنعك", "كيف تعمل", "هل انت ذكاء اصطناعي", "ما هذا التطبيق",
            "حدثني عن نفسك", "ماهي مهاراتك", "هل انت روبوت"
        ] * 25,
        "time_date_skill": [
            "كم الساعه", "ما هو الوقت الان", "الوقت الان", "اخبرني بالوقت", 
            "الساعه كم", "ما تاريخ اليوم", "اي يوم نحن", "ما التاريخ", "تاريخ اليوم",
            "الوقت والتاريخ", "كم الوقت", "الساعه كم الان"
        ] * 25,
        "stop_skill": [
            "توقف", "اسكت", "الغاء", "اخرس", "انهاء", "توقف عن الكلام", "اغلق", "كفى",
            "صمت", "قف", "توقف الان", "الغي الامر", "اخرس لو سمحت"
        ] * 25,
        "weather_skill": [
            "ما حاله الطقس", "كيف الجو اليوم", "هل ستمطر اليوم", "درجه الحراره الان",
            "توقعات الطقس غدا", "هل الجو بارد", "اخبرني بحاله الجو", "كيف هو المناخ",
            "هل ستمطر", "هل الطقس مشمس", "الطقس في مدينتي"
        ] * 25
    }

    texts = []
    labels = []

    for intent in data["intents"]:
        tag = intent["tag"]
        patterns = list(intent["patterns"])
        if tag in extra_patterns:
            patterns.extend(extra_patterns[tag])
            
        for pat in patterns:
            cleaned = normalize_arabic(pat)
            if len(cleaned) > 1:
                texts.append(cleaned)
                labels.append(tag)

    print(f"إجمالي الأنماط التدريبية بعد التعزيز: {len(texts)}")
    classes = sorted(list(set(labels)))
    print(f"عدد فئات النوايا المعتمدة: {len(classes)} -> {classes}")

    # تقسيم البيانات لتقييم النموذج
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.15, random_state=42, stratify=labels
    )

    print("جاري استخراج الخصائص النصية باستخدام TF-IDF...")
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=4000,
        sublinear_tf=True
    )
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    print("جاري تدريب مصنف الانحدار اللوجستي متوازن الفئات...")
    clf = LogisticRegression(
        max_iter=400,
        C=3.0,
        class_weight='balanced',
        solver='lbfgs'
    )
    clf.fit(X_train_vec, y_train)

    accuracy = clf.score(X_test_vec, y_test)
    print(f"دقة النموذج على مجموعة الاختبار: {accuracy * 100:.2f}%")

    # تدريب النموذج النهائي على كامل البيانات للحصول على أعلى دقة استدلال
    X_all_vec = vectorizer.fit_transform(texts)
    clf.fit(X_all_vec, labels)

    # استخراج الأوزان بصيغة JSON خفيفة الوزن للأندرويد
    vocab = vectorizer.vocabulary_
    # تحويل مفاتيح وقيم القاموس إلى أنواع بيانات قياسية
    vocab_clean = {k: int(v) for k, v in vocab.items()}
    idf_list = [float(val) for val in vectorizer.idf_]
    model_classes = [str(c) for c in clf.classes_]
    weights_matrix = [[float(val) for val in row] for row in clf.coef_]
    intercept_list = [float(val) for val in clf.intercept_]

    model_weights_payload = {
        "format": "ovos_arabic_nlu_json_weights",
        "version": "1.0",
        "language": "ar",
        "ngram_range": [1, 2],
        "sublinear_tf": True,
        "classes": model_classes,
        "vocabulary": vocab_clean,
        "idf": idf_list,
        "weights": weights_matrix,
        "bias": intercept_list
    }

    # مجلد أصول أندرويد
    assets_dir = os.path.join("app", "src", "main", "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # 1. حفظ أوزان النموذج JSON
    weights_path = os.path.join(assets_dir, "model_weights.json")
    with open(weights_path, "w", encoding="utf-8") as f:
        json.dump(model_weights_payload, f, ensure_ascii=False)
    print(f"تم تصدير أوزان النموذج بنجاح إلى: {weights_path}")
    print(f"حجم ملف الأوزان: {os.path.getsize(weights_path) / 1024:.2f} كيلوبايت")

    # 2. نسخة باسم model.json في الأصول
    model_json_path = os.path.join(assets_dir, "model.json")
    with open(model_json_path, "w", encoding="utf-8") as f:
        json.dump(model_weights_payload, f, ensure_ascii=False)

    # 3. حفظ نموذج بايثون كامل بصيغة joblib للاستخدام المباشر في بايثون/Chaquopy
    joblib_bundle = {
        "vectorizer": vectorizer,
        "classifier": clf,
        "classes": model_classes
    }
    joblib_path = os.path.join(assets_dir, "arabic_nlu_model.joblib")
    joblib.dump(joblib_bundle, joblib_path, compress=3)
    print(f"تم تصدير نموذج بايثون المضغوط إلى: {joblib_path}")

    # اختبار استدلال تجريبي
    print("\n--- فحص جودة الاستدلال بعد التدريب النهائي ---")
    test_queries = [
        "مرحبا كيف حالك يا صديقي",
        "عرفني بنفسك ومن تكون",
        "كم الوقت والساعة الآن",
        "ما هي عاصمة دولة مصر",
        "نصائح للبقاء بصحة جيدة ونشاط دائم",
        "صف بنية الذرة والنيوترونات",
        "احسب مساحة الدائرة أو ناتج ضرب أرقام",
        "ألف قصة جميلة عن طائر صغير",
        "توقف لو سمحت واسكت",
        "كيف الطقس وهل الجو معتدل"
    ]

    for q in test_queries:
        q_norm = normalize_arabic(q)
        vec = vectorizer.transform([q_norm])
        pred = clf.predict(vec)[0]
        probs = clf.predict_proba(vec)[0]
        conf = float(np.max(probs))
        print(f"سؤال: '{q}'\n  -> النية المحددة: {pred} (درجة الثقة: {conf * 100:.1f}%)")

if __name__ == "__main__":
    train_and_export()
