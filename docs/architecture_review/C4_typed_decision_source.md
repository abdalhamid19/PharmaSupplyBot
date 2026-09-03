# C4 — Type the decision source

**Strength:** Strong
**Tag:** in-process

## Files

- `src/core/manual_review/manual_review_helpers.py` (produces the magic string at `:100, :151, :156`)
- `src/tawreed/api/tawreed_api_flow_matching.py:199` (parses by `startswith`)
- `src/tawreed/api/tawreed_api_matching.py:148` (parses by `startswith`)
- `src/tawreed/order/tawreed_order_summary_build.py:50` (parses by `startswith`)
- `src/core/matching/matching_types.py` (add the field here)

## Problem

Four modules share knowledge of one magic string — `"Approved by saved manual review"` — produced in one place, parsed back by `startswith` in three others. The same string also carries the diagnostic score `999.0`, fabricated in two places (`_find_manual_review_match` in `manual_review_helpers.py`, mirrored in `tawreed_api_matching.py:107-122`).

This is the canonical shallow interface: a string protocol that has to be a typed enum. Knowledge of the convention is spread across four files; any change to the convention (rephrasing, adding a new source) breaks callers in three different packages.

## Solution

Add a typed `source: DecisionSource` field (or a factory `manual_review_decision(match, note)`) to `core.matching_types.MatchDecision`. Delete every `startswith("Approved by saved manual review")` parse. Move the `999.0` score fabrication to one place — the factory.

## Before / After

### Before — one string, four readers, one writer

```mermaid
flowchart LR
  H[manual_review_helpers.py<br/>fab: 'Approved by saved manual review (ID match).'<br/>score 999.0]
  H -->|produces| S(("'Approved by saved manual review'"))
  S -.startswith.-> A1[tawreed_api_flow_matching.py:199]
  S -.startswith.-> A2[tawreed_api_matching.py:148]
  S -.startswith.-> O[tawreed_order_summary_build.py:50]
  classDef leak stroke:#dc2626,stroke-width:2px;
  class S,A1,A2,O leak
```

### After — the source is data, not convention

```python
class DecisionSource(str, Enum):
    SCORING = "scoring"
    MANUAL_REVIEW_SAVED = "manual_review_saved"
    MANUAL_REVIEW_FORCED = "manual_review_forced"

@dataclass
class MatchDecision:
    ...
    source: DecisionSource = DecisionSource.SCORING
    note: str = ""
```

```mermaid
flowchart LR
  F[manual_review_decision(match, note)<br/>source = MANUAL_REVIEW_SAVED<br/>score 999.0] --> M[MatchDecision]
  M -->|match.source == DecisionSource.MANUAL_REVIEW_SAVED| A1[tawreed_api_flow_matching]
  M --> A2[tawreed_order_summary_build]
  M --> A3[any future caller]
  classDef deep fill:#0f172a,stroke:#0f172a,color:#fff;
  class F,M deep
```

## Wins

- knowledge concentrates in one type
- string parse bugs vanish (no `startswith`, no brittle rephrases)
- interface: provenance is data, not convention
- one place to evolve the diagnostic score
- leverage: any new caller reads `match.source` instead of learning the string
- locality: changing the convention is a one-file edit
