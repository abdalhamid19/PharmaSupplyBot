"""Quick: trace match_brand for items that hit the bilingual secondary flow."""
import os
import sys
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
os.chdir(REPO)

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['COHERE_API_KEY'] = 'kC7J5jmq5nOECPeHumKHWFYi1Dp1kBvtstAzHXLU'
os.environ['COHERE_RATE_LIMIT_PER_MIN'] = '15'
os.environ['COHERE_BATCH_SIZE'] = '50'
os.environ['MATCH_ARTIFACT_PATH'] = 'artifacts/match_traces/single_item.jsonl'

artifact = REPO / os.environ['MATCH_ARTIFACT_PATH']
artifact.parent.mkdir(parents=True, exist_ok=True)
if artifact.exists():
    artifact.unlink()

cmd = [
    sys.executable,
    'run.py', 'order',
    '--config', 'state/config.yaml',
    '--excel', 'data/input/order_items/0000000000006777.xlsx',
    '--limit', '4',
    '--all-profiles',
    '--excel-target', 'البركة شركات',
    '--excel-target-path', 'البركة شركات=data/input/excel target/البركة شركات.xlsx',
    '--match-only',
    '--execution-mode', 'api',
    '--item-workers', '1',
    '--matching-risk-policy', 'safe',
    '--flagged-match-action', 'manual-review-only',
    '--stop-flag', 'artifacts/run-control/order/order_stop.flag',
]

result = subprocess.run(cmd, env=os.environ, capture_output=True, text=True, encoding='utf-8')
print('\n'.join(result.stdout.splitlines()[-15:]))
print('return code:', result.returncode)
if artifact.exists():
    print(f'trace: {artifact.relative_to(REPO)} ({artifact.stat().st_size} bytes, {sum(1 for _ in artifact.open(encoding="utf-8"))} lines)')
