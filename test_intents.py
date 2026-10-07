import sys
import io
import re
import pandas as pd
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
parquet_path = r'C:\Users\Dell\.cache\kagglehub\datasets\omgits0mar\arabic-instruct-chatbot-dataset\versions\1\train-00000-of-00001-10520e8228c2c104.parquet'
df = pd.read_parquet(parquet_path)
df_clean = df[~df['output'].str.contains('<nooutput>', na=False)].dropna(subset=['instruction', 'output']).copy()

def classify_intent(text):
    t = text.lower()
    if any(k in t for k in ['مرحبا', 'أهلا', 'صباح الخير', 'مساء الخير', 'سلام عليكم', 'كيف حالك', 'من أنت']):
        return 'greeting_skill'
    elif any(k in t for k in ['صحة', 'غذائ', 'طعام', 'تمرين', 'نوم', 'جسم', 'دواء', 'مرض', 'فيتامين', 'سعرات', 'رياضة', 'وزن', 'ألم', 'علاج']):
        return 'health_wellness_skill'
    elif any(k in t for k in ['ذرة', 'كيمياء', 'فيزياء', 'حاسوب', 'كمبيوتر', 'برمج', 'كود', 'بروتون', 'خلية', 'فضاء', 'كوكب', 'جين', 'إلكترون', 'تقنية', 'ذكاء اصطناعي']):
        return 'science_tech_skill'
    elif any(k in t for k in ['عاصمة', 'تاريخ', 'دولة', 'حرب', 'معركة', 'قيصر', 'رئيس', 'نابليون', 'حضارة', 'قارة', 'نهر', 'مدينة', 'إمبراطور']):
        return 'history_geography_skill'
    elif any(k in t for k in ['احسب', 'حساب', 'رقم', 'معادلة', 'كسر', 'رياضيات', 'هندسة', 'نسبة', 'مئوية', 'ضرب', 'قسمة']):
        return 'math_logic_skill'
    elif any(k in t for k in ['ترجم', 'مرادف', 'ضد', 'إعراب', 'نحو', 'صرف', 'معنى كلمة', 'لغوي', 'أفعال تعني']):
        return 'language_translation_skill'
    elif any(k in t for k in ['قصة', 'رواية', 'قصيدة', 'شعر', 'أبيات', 'تأليف']):
        return 'creative_writing_skill'
    elif any(k in t for k in ['قائمة', 'خطوات', 'نصائح', 'اقتراح', 'خطة', 'نظم', 'جدول']):
        return 'daily_assistant_skill'
    else:
        return 'general_knowledge_skill'

df_clean['intent'] = df_clean['instruction'].apply(classify_intent)
print("Intent distribution across clean dataset:")
print(df_clean['intent'].value_counts())
