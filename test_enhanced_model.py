# -*- coding: utf-8 -*-
import sys
import io
import json
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def normalize_arabic(text: str) -> str:
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

with open("intents.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# توسيع أنماط التحيات والنظام
extra_patterns = {
    "greeting_skill": [
        "مرحبا", "مرحبا بك", "اهلا", "اهلا وسهلا", "السلام عليكم", "سلام عليكم",
        "صباح الخير", "مساء الخير", "تحياتي", "كيف حالك", "شو اخبارك", "كيفك",
        "هلا", "مرحبا بك يا مساعد", "السلام عليكم ورحمة الله", "صباح النور", "مساء النور"
    ] * 20,
    "assistant_info_skill": [
        "من انت", "ما اسمك", "عرفني بنفسك", "ما هي قدراتك", "ماذا تفعل", 
        "ما وظيفتك", "من صنعك", "كيف تعمل", "هل انت ذكاء اصطناعي", "ما هذا التطبيق"
    ] * 20,
    "time_date_skill": [
        "كم الساعه", "ما هو الوقت الان", "الوقت الان", "اخبرني بالوقت", 
        "الساعه كم", "ما تاريخ اليوم", "اي يوم نحن", "ما التاريخ", "تاريخ اليوم"
    ] * 20,
    "stop_skill": [
        "توقف", "اسكت", "الغاء", "اخرس", "انهاء", "توقف عن الكلام", "اغلق", "كفى", "صمت", "قف"
    ] * 20
}

texts = []
labels = []

for intent in data["intents"]:
    tag = intent["tag"]
    pats = list(intent["patterns"])
    if tag in extra_patterns:
        pats.extend(extra_patterns[tag])
    for pat in pats:
        cleaned = normalize_arabic(pat)
        if len(cleaned) > 1:
            texts.append(cleaned)
            labels.append(tag)

X_train, X_test, y_train, y_test = train_test_split(texts, labels, test_size=0.15, random_state=42, stratify=labels)

vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=5000, sublinear_tf=True)
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

clf = LogisticRegression(max_iter=400, C=3.0, class_weight='balanced')
clf.fit(X_train_vec, y_train)

score = clf.score(X_test_vec, y_test)
print(f"Accuracy with balanced weights and augmented system intents: {score:.4f}")

test_queries = [
    "مرحبا كيف حالك",
    "من انت وما وظيفتك",
    "كم الساعه الان",
    "ما هي عاصمه فرنسا",
    "كيف احافظ علي صحتي ونشاطي",
    "ما هي الذره والالكترونات",
    "احسب حاصل ضرب 5 في 12",
    "اكتب قصه قصيره عن مغامره في الغابه",
    "توقف عن الحديث",
    "ما حاله الطقس اليوم"
]

print("\n--- نتائج الاستدلال المحسنة ---")
classes = list(clf.classes_)
for q in test_queries:
    q_norm = normalize_arabic(q)
    vec = vectorizer.transform([q_norm])
    pred = clf.predict(vec)[0]
    probs = clf.predict_proba(vec)[0]
    conf = np.max(probs)
    print(f"المدخل: '{q}' -> النية: {pred} (درجة الثقة: {conf:.2f})")
