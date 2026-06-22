# PROJECT_MAP

## [TECH_STACK]
- Python 3.10+ application with Streamlit UI, unittest tests, and CockroachDB
  persistence through psycopg2.
- Manual review decisions are stored in `manual_review_decisions` and surfaced
  in the Streamlit Manual Review tab.

## [SYSTEM_FLOW]
- Order and match runs create artifact run IDs formatted like `YYYYMMDD_HHMM`.
- Manual Review saves human or automatic decisions with the run ID attached.
- Saved Corrections displays those persisted decisions for review, export, and
  follow-up match-only searches.

## [ARCHITECTURE]
- `src/core/manual_review_store.py` owns the persisted decision model and store.
- `src/ui/streamlit_manual_review_page_saved.py` owns the Saved Corrections
  table presentation.
- Saved Corrections now exposes `run_date` from the existing `run_id` value
  without changing the database schema.

## [ORPHANS & PENDING]
- None for the Saved Corrections run-date display change.
