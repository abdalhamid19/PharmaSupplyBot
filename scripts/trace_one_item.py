"""Trace ONE item through the bilingual secondary matcher and print every step."""
import os
from dotenv import load_dotenv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
load_dotenv(REPO / ".env", override=False)
sys.path.insert(0, str(REPO))

os.environ['MATCH_ARTIFACT_PATH'] = 'artifacts/match_traces/one_item.jsonl'

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

item = Item(code='', name='ALFATHROMB 5 MCG 20 TABS', qty=1)
print(f'item: {item.name}')
print(f'catalog size: {len(catalog)}')
print()

r = find_best_match_in_target(item, 'البركة شركات', catalog, app_cfg.matching)
print(f'final decision: best_match={r.decision.best_match is not None}')
print(f'final reason  : {r.decision.final_reason}')

if artifact.exists():
    import json
    print()
    print('--- per-candidate trace ---')
    recs = [json.loads(l) for l in artifact.read_text(encoding='utf-8').splitlines() if l.strip()]
    recs.sort(key=lambda r: -r['final_score'])
    for i, rec in enumerate(recs[:5], 1):
        print(f'#{i} ar={rec["ar_row"]!r}')
        print(f'    tier1={rec["tier1_tawreed"]}')
        print(f'    tier2={rec["tier2_karem505"]}')
        print(f'    tier3={rec["tier3_cache"]["score"]:.2f} trans={rec["tier3_cache"]["translation"]!r}')
        print(f'    compat={rec["compatibility_factor"]:.2f}  final={rec["final_score"]:.2f}')
        print(f'    reason={rec["winning_reason"]!r}')
        print()
    print(f'(... {len(recs)-5} more candidates tested)' if len(recs) > 5 else '')
