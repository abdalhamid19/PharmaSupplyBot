"""Run the order pipeline with match-trace artifact enabled.

Wraps ``run.py order`` so the Arabic command-line args survive the
PowerShell encoding mangle: we set env vars and shell out via
subprocess with a list argv.
"""
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
os.chdir(REPO)

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUNBUFFERED'] = '1'
os.environ['COHERE_API_KEY'] = 'kC7J5jmq5nOECPeHumKHWFYi1Dp1kBvtstAzHXLU'
os.environ['COHERE_RATE_LIMIT_PER_MIN'] = '15'
os.environ['COHERE_BATCH_SIZE'] = '50'
os.environ['MATCH_ARTIFACT_PATH'] = 'artifacts/match_traces/wardany_20260905_1300.jsonl'

artifact = REPO / os.environ['MATCH_ARTIFACT_PATH']
artifact.parent.mkdir(parents=True, exist_ok=True)
if artifact.exists():
    artifact.unlink()

cmd = [
    sys.executable,
    'run.py', 'order',
    '--config', 'state/config.yaml',
    '--excel', 'data/input/order_items/0000000000006777.xlsx',
    '--limit', '50',
    '--all-profiles',
    '--excel-target', 'البركة شركات',
    '--excel-target-path', 'البركة شركات=data/input/excel target/البركة شركات.xlsx',
    '--match-only',
    '--execution-mode', 'api',
    '--item-workers', '1',
    '--prevented-items-excel', 'data/input/prevented_items/drugprevented.xlsx',
    '--matching-risk-policy', 'safe',
    '--flagged-match-action', 'manual-review-only',
    '--stop-flag', 'artifacts/run-control/order/order_stop.flag',
]

print('CMD:', ' '.join(cmd))
result = subprocess.run(cmd, env=os.environ, capture_output=True, text=True, encoding='utf-8')
print('=== stdout (last 30 lines) ===')
print('\n'.join(result.stdout.splitlines()[-30:]))
print('=== return code:', result.returncode)
if result.stderr:
    print('=== stderr (last 10 lines) ===')
    print('\n'.join(result.stderr.splitlines()[-10:]))

if artifact.exists():
    lines = sum(1 for _ in artifact.open(encoding='utf-8'))
    print(f'\n=== trace artifact: {artifact.relative_to(REPO)} ({artifact.stat().st_size} bytes, {lines} lines) ===')
else:
    print('\n!! no trace artifact written')
