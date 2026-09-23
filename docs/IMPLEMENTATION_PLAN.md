# Implementation Plan

## Current findings

- The supplied files are in `DataSet/`, not the `data/raw/` layout described by the README.
- `transactions.csv` has 590,742 rows and 397 columns; `identity.csv` has 144,432 rows and 41 columns.
- Transaction timestamps exactly match `2016-07-02 + TransactionDT` seconds, and `ProductCD == W` agrees with `channel == in_person` for every row.
- All 14,975 transaction links referenced by closed cases and the case pack exist.
- A card is not reliably identified by one `card2-card6` signature. Some cards have multiple partially populated signatures. The resolver therefore anchors known links and marks non-forced assignments as unresolved.
- The 20 benchmark cases are all present and use valid flagged transaction, customer, and card IDs.

## Build order

### 1. Local data contract

- Keep the supplied CSVs immutable and outside graph-load code.
- Run `python scripts.verify_dataset.py --json` before every load.
- Run `python scripts.derive_card_ids.py` to create `artifacts/transaction_cards.csv`.
- Treat `mapping_source=known_anchor` as verified; do not silently use `unresolved` rows for card-level conclusions.

### 2. Evidence engine

- Build a local evidence profile for each benchmark case: flagged transaction, customer/card history, identity record, device profile, billing region, velocity window, and similar closed cases.
- Use the derived mapping only where verified or forced by constraints.
- Keep transaction outcomes out of transaction records. Closed-case outcome is the only supplied label.

### 3. Deterministic policy

- Use `agent.policy` for exact action identifiers and approval routes.
- Add R1-R10 tests before connecting an LLM.
- Serialize `initial` actions before any evidence request and `final` actions afterward.
- Validate SAR consistency and every referenced ID before writing an answer file.

### 4. Graph and retrieval

- Load the core graph first: Customer, Card, Transaction, and ClosedCase.
- Add DeviceProfile, EmailDomain, BillingRegion, and temporal `NEXT` edges.
- Install pattern and discovery queries, then connect TigerGraph MCP.
- Retrieve structured subgraph summaries and temporal-filtered closed cases; never pass unbounded raw rows to the model.

### 5. Agent and evaluation

- Implement the bounded investigation state machine with simulated evidence requests.
- Run cases chronologically by `opened_at` and enforce `closed_at < opened_at` for memory retrieval.
- Generate and validate all 20 answer files.
- Backtest on closed cases with a temporal holdout; calibrate probabilities only before touching the benchmark cases.

## Prior immediate task

Build the answer-schema validator and local investigation composer. The local profiler and deterministic pattern detectors are now available, including card testing, shared entities, CNP, new-device, out-of-region, account-takeover signals, and undocumented coordination. `artifacts/pattern_matches.json` contains detector output for all 20 cases. TigerGraph, MCP, external documents, and optional Jev integration should wait until the local composer can explain one benchmark case end to end.

## Completed local detection slice

- Added `agent/detection/patterns.py` with pure, JSON-compatible detectors.
- Added `scripts/detect_patterns.py` to generate the batch artifact.
- Added `test_detection.py` with focused HHG-014, negative CNP, new-device, and shared-overlap tests.
- HHG-014 detects the shared Samsung device ring and preserves its connected cards/customers as evidence.
- Undocumented coordination requires a multi-customer ring; ordinary two-customer overlaps remain shared-entity evidence only.

## Completed answer contract slice

- Added `agent/investigation/validator.py` for schema, ID, exposure, SAR, action-route, rule-citation, and temporal-memory contract checks.
- Added `agent/investigation/composer.py` for a deterministic local draft investigation record.
- Added `scripts/compose_answers.py` and `scripts/validate_answers.py` for batch generation and release validation.
- Added `test_investigation.py` for composed-answer round trips and invalid-answer rejection.

## Next task

Integrate the local investigation contract with TigerGraph schema/load jobs and replace local detector evidence with bounded graph query results. Keep the local composer and validator as the reference implementation while graph integration proceeds.

## Completed calibration and evidence-request slice

- Added `agent/investigation/calibration.py`, a dependency-free isotonic calibrator for temporal backtest predictions.
- Added `scripts/fit_calibrator.py` to save calibration knots as JSON.
- Added deterministic simulated evidence requests to the local composer:
	- customer reports request validation and assume a denial;
	- weak non-undocumented signals request validation and assume no reply after 24 hours;
	- strong coordinated evidence stops without an unnecessary request.
- Draft answers now preserve `initial`, `final`, `what_changed`, and `evidence_requests` consistently.
- The regenerated 20-case batch contains 10 evidence-request transitions and passes validation with zero failures.

## Completed graph-preparation prerequisite

- The local data layer now loads `artifacts/transaction_cards.csv` as the source of transaction-to-card relationships.
- Card history no longer falls back to all transactions for a customer, preventing cross-card evidence leakage.
- Unresolved mapping rows remain excluded from card indexes rather than being treated as verified relationships.
- Added a focused regression test covering two cards belonging to one customer.

The next graph step remains schema/load implementation in TigerGraph. The local prerequisite is now ready for parity checks once `pyTigerGraph` and a configured Savanna workspace are available.