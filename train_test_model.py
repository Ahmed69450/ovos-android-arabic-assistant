# -*- coding: utf-8 -*-
import sys
import io
import json
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

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

texts = []
labels = []

for intent in data["intents"]:
    tag = intent["tag"]
    for pat in intent["patterns"]:
        cleaned = normalize_arabic(pat)
        if len(cleaned) > 1:
            texts.append(cleaned)
            labels.append(tag)

print(f"Total training examples: {len(texts)}")
print(f"Total classes: {len(set(labels))}")

X_train, X_test, y_train, y_test = train_test_split(texts, labels, test_size=0.15, random_state=42, stratify=labels)

vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=4000, sublinear_tf=True)
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

clf = LogisticRegression(max_iter=300, C=2.0)
clf.fit(X_train_vec, y_train)

score = clf.score(X_test_vec, y_test)
print(f"Model Accuracy on Test Set: {score:.4f}")

# تجربة بعض العبارات
test_queries = [
    "مرحبا كيف حالك",
    "من انت وما وظيفتك",
    "كم الساعه الان",
    "ما هي عاصمه مصر",
    "كيف احافظ علي صحتي ونشاطي",
    "ما هي الذره والالكترونات",
    "احسب حاصل ضرب 5 في 12",
    "اكتب قصه قصيره عن مغامره في الغابه",
    "توقف عن الحديث"
]

print("\n--- تجربة استدلال النوايا ---")
for q in test_queries:
    q_norm = normalize_arabic(q)
    vec = vectorizer.transform([q_norm])
    pred = clf.predict(vec)[0]
    probs = clf.predict_proba(vec)[0]
    conf = np.max(probs)
    print(f"المدخل: '{q}' -> النية: {pred} (درجة الثقة: {conf:.2f})")
