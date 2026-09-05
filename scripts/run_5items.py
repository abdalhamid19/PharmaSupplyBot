"""Run a small order with match-trace artifact and time it."""
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
os.chdir(REPO)

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['COHERE_API_KEY'] = 'kC7J5jmq5nOECPeHumKHWFYi1Dp1kBvtstAzHXLU'
os.environ['COHERE_RATE_LIMIT_PER_MIN'] = '15'
os.environ['COHERE_BATCH_SIZE'] = '50'
os.environ['MATCH_ARTIFACT_PATH'] = 'artifacts/match_traces/wardany_5items.jsonl'

artifact = REPO / os.environ['MATCH_ARTIFACT_PATH']
artifact.parent.mkdir(parents=True, exist_ok=True)
if artifact.exists():
    artifact.unlink()

cmd = [
    sys.executable,
    'run.py', 'order',
    '--config', 'state/config.yaml',
    '--excel', 'data/input/order_items/0000000000006777.xlsx',
    '--limit', '5',
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

t0 = time.time()
result = subprocess.run(cmd, env=os.environ, capture_output=True, text=True, encoding='utf-8')
elapsed = time.time() - t0

print(f'elapsed: {elapsed:.1f}s')
print('=== stdout (last 15) ===')
print('\n'.join(result.stdout.splitlines()[-15:]))
print('=== return code:', result.returncode)
if artifact.exists():
    lines = sum(1 for _ in artifact.open(encoding='utf-8'))
    size_kb = artifact.stat().st_size / 1024
    print(f'\n=== trace: {artifact.relative_to(REPO)} ({size_kb:.1f} KB, {lines} lines) ===')
else:
    print('!! no trace artifact')
