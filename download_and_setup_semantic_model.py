# -*- coding: utf-8 -*-
"""
تحميل ملفات نموذج ONNX المكمم والـ Tokenizer وتجهيز موجه المعاني
"""

import os
import sys
import time
import json
import urllib.request

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ASSETS_DIR = os.path.join("app", "src", "main", "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

MODEL_URL = "https://huggingface.co/Xenova/paraphrase-multilingual-MiniLM-L12-v2/resolve/main/onnx/model_quantized.onnx"
TOKENIZER_URL = "https://huggingface.co/Xenova/paraphrase-multilingual-MiniLM-L12-v2/resolve/main/tokenizer.json"
CONFIG_URL = "https://huggingface.co/Xenova/paraphrase-multilingual-MiniLM-L12-v2/resolve/main/config.json"

TARGET_MODEL_PATH = os.path.join(ASSETS_DIR, "semantic_model.onnx")
TARGET_TOKENIZER_PATH = os.path.join(ASSETS_DIR, "tokenizer.json")
TARGET_CONFIG_PATH = os.path.join(ASSETS_DIR, "semantic_config.json")

def download_file_with_progress(url: str, dest_path: str, desc: str):
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000:
        print(f"[{desc}] موجود مسبقاً بحجم {os.path.getsize(dest_path) / (1024*1024):.2f} ميغابايت - تم التخطي.")
        return True

    print(f"[{desc}] جاري التحميل من Hugging Face...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            block_size = 512 * 1024  # 512 KB
            start_time = time.time()
            
            with open(dest_path + ".tmp", "wb") as f:
                while True:
                    chunk = resp.read(block_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        pct = (downloaded / total_size) * 100
                        mb = downloaded / (1024 * 1024)
                        tot_mb = total_size / (1024 * 1024)
                        speed = mb / max(0.1, time.time() - start_time)
                        sys.stdout.write(f"\r  -> تقدم التحميل: {pct:.1f}% ({mb:.1f}/{tot_mb:.1f} MB) - السرعة: {speed:.2f} MB/s")
                        sys.stdout.flush()

            sys.stdout.write("\n")
            if os.path.exists(dest_path):
                os.remove(dest_path)
            os.rename(dest_path + ".tmp", dest_path)
            print(f"[{desc}] اكتمل التحميل بنجاح: {os.path.getsize(dest_path) / (1024*1024):.2f} ميغابايت.")
            return True
    except Exception as e:
        print(f"\n[خطأ] فشل تحميل {desc}: {e}")
        if os.path.exists(dest_path + ".tmp"):
            os.remove(dest_path + ".tmp")
        return False

def setup():
    print("=== بدء تنزيل وتجهيز نموذج ONNX الدلالي لأندرويد ===")
    
    # 1. Config
    download_file_with_progress(CONFIG_URL, TARGET_CONFIG_PATH, "Config JSON")

    # 2. Tokenizer (17 MB)
    download_file_with_progress(TOKENIZER_URL, TARGET_TOKENIZER_PATH, "Tokenizer JSON")

    # 3. Quantized ONNX Model (112 MB)
    download_file_with_progress(MODEL_URL, TARGET_MODEL_PATH, "Quantized ONNX Model")

if __name__ == "__main__":
    setup()
