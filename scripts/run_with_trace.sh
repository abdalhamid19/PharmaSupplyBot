#!/bin/bash
cd "$(dirname "$0")/.."
export PYTHONIOENCODING=utf-8
export COHERE_RATE_LIMIT_PER_MIN=15
export COHERE_BATCH_SIZE=50
export MATCH_ARTIFACT_PATH="artifacts/match_traces/wardany_20260905_1300.jsonl"
export PYTHONUNBUFFERED=1
.venv/Scripts/python.exe run.py order --config state/config.yaml --excel "data/input/order_items/0000000000006777.xlsx" --limit 50 --all-profiles --excel-target "البركة شركات" --excel-target-path "البركة شركات=data/input/excel target/البركة شركات.xlsx" --match-only --execution-mode api --item-workers 1 --prevented-items-excel "data/input/prevented_items/drugprevented.xlsx" --matching-risk-policy safe --flagged-match-action manual-review-only --stop-flag "artifacts/run-control/order/order_stop.flag" > logs/run_full.log 2>&1
