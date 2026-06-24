# PROJECT_MAP

## [TECH_STACK]
- Python 3.10+ application with Streamlit UI, unittest tests, and CockroachDB
  persistence through psycopg2.
- Optional Tawreed API execution backend reuses the saved Playwright storage
  state and a locally discovered endpoint contract.

## [SYSTEM_FLOW]
- Order and match runs create artifact run IDs formatted like `YYYYMMDD_HHMM`.
- In `auto`/`api` execution modes the order flow adds matched items through the
  Tawreed API; a wrong or missing contract falls back to the browser flow.
- The add-to-cart contract is discovered from captured browser requests and
  persisted to `state/tawreed_api_endpoints.json`.

## [ARCHITECTURE]
- `src/tawreed/tawreed_api.py` owns the API client and now refuses the
  cart-read endpoint (`.../carts/items`) as an add endpoint via
  `_is_trusted_add_to_cart_url`, so a stale contract cannot report a false
  `added-to-cart`.
- `src/tawreed/tawreed_api_contract_merge.py` discovery markers select only the
  real add endpoint (`.../carts/items/add`), never the bare cart-read route.
- `state/tawreed_api_endpoints.json` holds the trusted add endpoint contract.

## [ORPHANS & PENDING]
- Live re-verification of the `/carts/items/add` success response shape is
  pending a fresh (non-expired) access token.
