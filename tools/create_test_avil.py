"""
إنشاء ملف Excel صغير لاختبار AVIL 6 AMP
"""
import pandas as pd

data = {
    'كود': ['73396'],
    'إسم الصنف': ['AVIL 6 AMP'],
    'الكميه': [1]
}

df = pd.DataFrame(data)
output_file = 'test_avil_fix.xlsx'
df.to_excel(output_file, index=False)

print(f"Created: {output_file}")
print("\nTest with:")
print(f"python run.py order --profile wardany --excel {output_file} --limit 1 --match-only")
