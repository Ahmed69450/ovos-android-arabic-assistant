import sys
import io
import json
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
parquet_path = r'C:\Users\Dell\.cache\kagglehub\datasets\omgits0mar\arabic-instruct-chatbot-dataset\versions\1\train-00000-of-00001-10520e8228c2c104.parquet'
df = pd.read_parquet(parquet_path)
df_clean = df[~df['output'].str.contains('<nooutput>', na=False)].dropna(subset=['instruction', 'output'])

# حجم 5000 نموذج عشوائي أو كامل الداتاسيت
sample_5k = df_clean.head(5000).to_dict(orient='records')
json_str_5k = json.dumps(sample_5k, ensure_ascii=False)
print("Size of 5,000 items in JSON:", len(json_str_5k.encode('utf-8')) / (1024 * 1024), "MB")

json_str_all = json.dumps(df_clean.to_dict(orient='records'), ensure_ascii=False)
print("Size of all 51,200 items in JSON:", len(json_str_all.encode('utf-8')) / (1024 * 1024), "MB")
