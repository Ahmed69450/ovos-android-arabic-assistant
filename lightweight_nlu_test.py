# -*- coding: utf-8 -*-
import sys
import io
import json
import re
import math
import numpy as np

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class LightweightArabicNLU:
    """محرك استدلال خفيف الوزن بلغة بايثون النقية يعمل بدون أي مكتبات خارجية ثقيلة"""
    def __init__(self, weights_data):
        self.vocab = weights_data["vocabulary"]
        self.idf = weights_data["idf"]
        self.classes = weights_data["classes"]
        self.weights = weights_data["weights"]
        self.bias = weights_data["bias"]
        self.ngram_range = weights_data.get("ngram_range", [1, 2])
        self.sublinear_tf = weights_data.get("sublinear_tf", True)

    @staticmethod
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

    def tokenize(self, text: str):
        words = text.split()
        tokens = []
        # Unigrams
        tokens.extend(words)
        # Bigrams
        if self.ngram_range[1] >= 2:
            for i in range(len(words) - 1):
                tokens.append(f"{words[i]} {words[i+1]}")
        return tokens

    def predict(self, text: str):
        cleaned = self.normalize_arabic(text)
        tokens = self.tokenize(cleaned)
        
        counts = {}
        for t in tokens:
            if t in self.vocab:
                counts[t] = counts.get(t, 0) + 1
                
        if not counts:
            return {"intent": "general_knowledge_skill", "confidence": 0.0, "cleaned_text": cleaned}
            
        # بناء متجه TF-IDF
        vec = [0.0] * len(self.vocab)
        for term, cnt in counts.items():
            idx = self.vocab[term]
            tf = (1.0 + math.log(cnt)) if self.sublinear_tf else float(cnt)
            vec[idx] = tf * self.idf[idx]
            
        # L2 Normalization
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
            
        # Dot product مع الأوزان + الانحياز (Bias)
        logits = []
        for c_idx in range(len(self.classes)):
            score = self.bias[c_idx]
            c_weights = self.weights[c_idx]
            # ضرب نقطي متناثر (Sparse dot product)
            for term in counts:
                idx = self.vocab[term]
                score += c_weights[idx] * vec[idx]
            logits.append(score)
            
        # Softmax
        max_logit = max(logits)
        exp_scores = [math.exp(l - max_logit) for l in logits]
        total_exp = sum(exp_scores)
        probs = [s / total_exp for s in exp_scores]
        
        best_idx = probs.index(max(probs))
        return {
            "intent": self.classes[best_idx],
            "confidence": probs[best_idx],
            "all_probabilities": dict(zip(self.classes, probs)),
            "cleaned_text": cleaned
        }

print("LightweightArabicNLU definition validated successfully!")
