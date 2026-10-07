import sys
import io
import re
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
parquet_path = r'C:\Users\Dell\.cache\kagglehub\datasets\omgits0mar\arabic-instruct-chatbot-dataset\versions\1\train-00000-of-00001-10520e8228c2c104.parquet'

df = pd.read_parquet(parquet_path)
print("Data shape:", df.shape)

# تحقق من وجود نصوص غير صالحة أو <nooutput>
no_output = df['output'].str.contains('<nooutput>', na=False).sum()
print("Number of <nooutput>:", no_output)

# تنظيف البيانات
df_clean = df[~df['output'].str.contains('<nooutput>', na=False)].copy()
df_clean['instruction'] = df_clean['instruction'].astype(str).str.strip()
df_clean['output'] = df_clean['output'].astype(str).str.strip()
df_clean = df_clean[(df_clean['instruction'].str.len() > 3) & (df_clean['output'].str.len() > 3)]
print("Cleaned count:", len(df_clean))
