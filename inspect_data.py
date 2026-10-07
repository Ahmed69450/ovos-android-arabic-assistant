import sys
import io
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
parquet_path = r'C:\Users\Dell\.cache\kagglehub\datasets\omgits0mar\arabic-instruct-chatbot-dataset\versions\1\train-00000-of-00001-10520e8228c2c104.parquet'

df = pd.read_parquet(parquet_path)
print("Total rows:", len(df))
print("Null values in instruction:", df['instruction'].isna().sum())
print("Null values in output:", df['output'].isna().sum())

print("\n--- أول 10 عينات ---")
for idx, row in df.head(10).iterrows():
    inst = str(row['instruction']).strip()
    out = str(row['output']).strip()[:80].replace("\n", " ")
    print(f"[{idx}] س: {inst} | ج: {out}")
