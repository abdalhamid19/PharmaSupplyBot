"""Test match_brand artifact logging inline."""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

os.environ['MATCH_ARTIFACT_PATH'] = 'artifacts/match_traces/test_inline.jsonl'
os.environ['COHERE_API_KEY'] = 'kC7J5jmq5nOECPeHumKHWFYi1Dp1kBvtstAzHXLU'
os.environ['COHERE_RATE_LIMIT_PER_MIN'] = '15'
os.environ['COHERE_BATCH_SIZE'] = '50'

Path('artifacts/match_traces').mkdir(parents=True, exist_ok=True)
if Path('artifacts/match_traces/test_inline.jsonl').exists():
    Path('artifacts/match_traces/test_inline.jsonl').unlink()

from src.core.normalization.bilingual_brand_matcher import match_brand

cases = [
    ('CONCOR 5 MG 30 TABS', 'كونكور 5مجم 30قرص س ج'),
    ('PANADOL EXTRA 24 TABS', 'بنادول إكسترا 24قرص'),
    ('BLINK TEARS EYE DROPS 10 ML', 'قطرات بليتك كولاجين'),
    ('IBUPROFEN 400 MG 14 TABS', 'إيبروفين 400 مجم 14قرص'),
]
for en, ar in cases:
    m = match_brand(en, ar)
    print(f'{en:35s} -> {m.score:.2f}  {m.reason}')

print()
trace = Path('artifacts/match_traces/test_inline.jsonl')
if trace.exists():
    print(f'trace: {trace} ({trace.stat().st_size} bytes, {sum(1 for _ in trace.open(encoding="utf-8"))} lines)')
else:
    print('NO TRACE FILE WRITTEN')
