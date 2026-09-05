"""Run find_best_match_in_target for 5 items to exercise the secondary path."""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

os.environ['MATCH_ARTIFACT_PATH'] = 'artifacts/match_traces/findbest.jsonl'
os.environ['COHERE_API_KEY'] = 'kC7J5jmq5nOECPeHumKHWFYi1Dp1kBvtstAzHXLU'
os.environ['COHERE_RATE_LIMIT_PER_MIN'] = '15'
os.environ['COHERE_BATCH_SIZE'] = '50'

artifact = REPO / os.environ['MATCH_ARTIFACT_PATH']
artifact.parent.mkdir(parents=True, exist_ok=True)
if artifact.exists():
    artifact.unlink()

from src.core.excel_target.excel_target_matching import find_best_match_in_target
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

for name in [
    'CONCOR 5 MG 30 TABS',
    'PANADOL EXTRA 24 TABS',
    'BLINK TEARS EYE DROPS 10 ML',
    'IBUPROFEN 400 MG 14 TABS',
    'VOLTAREN 50 MG 20 TAB',
]:
    item = Item(code='', name=name, qty=1)
    r = find_best_match_in_target(item, 'البركة شركات', catalog, app_cfg.matching)
    if r.decision.best_match:
        en = r.decision.best_match.data.get('productNameEn', '')[:50]
        print(f'{name:30s} -> {en} ({r.decision.final_reason[:50]})')
    else:
        print(f'{name:30s} -> no match ({r.decision.final_reason[:50]})')

if artifact.exists():
    lines = sum(1 for _ in artifact.open(encoding='utf-8'))
    print(f'\ntrace: {lines} lines, {artifact.stat().st_size} bytes')
else:
    print('NO TRACE')
