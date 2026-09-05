"""Trace single item with all 4 items hard-stop after first non-match."""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

os.environ['MATCH_ARTIFACT_PATH'] = 'artifacts/match_traces/single.jsonl'
os.environ['COHERE_API_KEY'] = 'kC7J5jmq5nOECPeHumKHWFYi1Dp1kBvtstAzHXLU'
os.environ['COHERE_RATE_LIMIT_PER_MIN'] = '15'
os.environ['COHERE_BATCH_SIZE'] = '50'

artifact = REPO / os.environ['MATCH_ARTIFACT_PATH']
artifact.parent.mkdir(parents=True, exist_ok=True)
if artifact.exists():
    artifact.unlink()

from src.core.excel_target.excel_target_matching import _bilingual_secondary_match
from src.core.excel_target.excel_target_loader import load_target_catalog_from_excel
from src.core.config.config import load_config
from src.core.utils.excel import Item

app_cfg = load_config(REPO / 'state/config.yaml')
excel_cfg = app_cfg.excel_targets['البركة شركات']
catalog = load_target_catalog_from_excel(
    str(REPO / 'data/input/excel target/البركة شركات.xlsx'),
    excel_cfg,
    source_file='البركة شركات.xlsx',
)

print(f'catalog size: {len(catalog)}')
item = Item(code='', name='CONCOR 5 MG 30 TABS', qty=1)
print('Calling _bilingual_secondary_match...')
fb = _bilingual_secondary_match(item, catalog, min_score=0.7)
if fb and fb.best_match:
    en = fb.best_match.data.get('productNameEn', '')[:50]
    print(f'matched: {en}')
else:
    print('no match')

if artifact.exists():
    lines = sum(1 for _ in artifact.open(encoding='utf-8'))
    print(f'trace: {lines} lines')
else:
    print('NO TRACE')
