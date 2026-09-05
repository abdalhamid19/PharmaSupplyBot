"""Debug whether env var reaches match_brand."""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

os.environ['MATCH_ARTIFACT_PATH'] = 'artifacts/match_traces/debug.jsonl'

from src.core.normalization.bilingual_brand_matcher import match_brand
import src.core.normalization.bilingual_brand_matcher as bbm

print('module _artifact_path:', bbm._artifact_path)
print('env MATCH_ARTIFACT_PATH:', os.environ.get('MATCH_ARTIFACT_PATH'))
print('module file:', bbm.__file__)

m = match_brand('CONCOR 5 MG', 'كونكور 5مجم')
print('match result:', m.score, m.reason)
print('module _artifact_path after:', bbm._artifact_path)
art = bbm._resolve_artifact_path()
print('resolved:', art)

m = match_brand('CONCOR 5 MG', 'كونكور 5مجم')
print('match result:', m.score, m.reason)
print('module _artifact_path after:', m._artifact_path)
