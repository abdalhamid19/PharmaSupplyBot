import sys
sys.path.insert(0, '.')
from src.core.excel_target.excel_target_matching import _bilingual_secondary_match
from src.core.excel_target.excel_target_loader import load_target_catalog_from_excel
from src.core.config.config import load_config
from src.core.utils.excel import Item
from pathlib import Path

app_cfg = load_config(Path('state/config.yaml'))
excel_cfg = app_cfg.excel_targets['البركة شركات']
catalog = load_target_catalog_from_excel('data/input/excel target/البركة شركات.xlsx', excel_cfg, source_file='البركة شركات.xlsx')

for name in ['BLINK TEARS EYE DROPS 10 ML', 'CONCOR 5 MG 30 TABS']:
    item = Item(code='', name=name, qty=1)
    fb = _bilingual_secondary_match(item, catalog, min_score=0.7)
    if fb and fb.best_match:
        en = fb.best_match.data.get('productNameEn', '')[:40]
        print(f'{name}: {en}')
    else:
        print(f'{name}: no match')
