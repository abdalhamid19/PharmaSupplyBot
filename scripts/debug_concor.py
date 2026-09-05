"""Trace find_best_match_in_target for CONCOR and print debug."""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

os.environ['MATCH_ARTIFACT_PATH'] = 'artifacts/match_traces/concor.jsonl'
os.environ['COHERE_API_KEY'] = 'kC7J5jmq5nOECPeHumKHWFYi1Dp1kBvtstAzHXLU'
os.environ['COHERE_RATE_LIMIT_PER_MIN'] = '15'
os.environ['COHERE_BATCH_SIZE'] = '50'

artifact = REPO / os.environ['MATCH_ARTIFACT_PATH']
artifact.parent.mkdir(parents=True, exist_ok=True)
if artifact.exists():
    artifact.unlink()

from src.core.excel_target.excel_target_matching import (
    find_best_match_in_target, _bilingual_secondary_match, _finalize_fallback,
)
from src.core.excel_target.excel_target_loader import load_target_catalog_from_excel
from src.core.config.config import load_config
from src.core.utils.excel import Item

app_cfg = load_config(REPO / 'state/config.yaml')
print('enable_bilingual_secondary_match:', app_cfg.matching.enable_bilingual_secondary_match)
excel_cfg = app_cfg.excel_targets['البركة شركات']
catalog = load_target_catalog_from_excel(
    str(REPO / 'data/input/excel target/البركة شركات.xlsx'),
    excel_cfg,
    source_file='البركة شركات.xlsx',
)

item = Item(code='', name='CONCOR 5 MG 30 TABS', qty=1)
print('Calling find_best_match_in_target...')
r = find_best_match_in_target(item, 'البركة شركات', catalog, app_cfg.matching)
print(f'best_match: {r.decision.best_match is not None}')
print(f'final_reason: {r.decision.final_reason[:80]}')
if r.decision.best_match:
    print(f'match: {r.decision.best_match.data.get("productNameEn", "")[:50]}')

# Direct call
print()
print('Direct _bilingual_secondary_match...')
fb = _bilingual_secondary_match(item, catalog, min_score=0.7)
print(f'fallback: {fb}')
if fb and fb.best_match:
    print(f'match: {fb.best_match.data.get("productNameEn", "")[:50]}')

if artifact.exists():
    print(f'\ntrace: {sum(1 for _ in artifact.open(encoding="utf-8"))} lines')
