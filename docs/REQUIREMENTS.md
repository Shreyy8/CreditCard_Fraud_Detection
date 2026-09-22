# System Requirements

## Agentic Fraud Investigation System

**Version:** 1.0  
**Status:** Implementation baseline  
**Date:** 2026-09-22  
**Related documents:** [PRD.md](PRD.md), [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md), [README.md](../README.md), [DataSet/README.md](../DataSet/README.md)

## 1. Purpose

This document defines the requirements for the benchmark-ready fraud investigation system. It converts the product goals into implementation, validation, and submission requirements that can be tested or demonstrated.

## 2. Product Boundary

The system accepts a fraud-alert case from the supplied case pack and produces an auditable investigation record, a policy-compliant suspicious activity report decision, and initial/final next-best actions.

The system is decision support. It may execute only actions routed as `auto`. Actions routed as `L1` or `L2` must remain recommendations awaiting human approval.

The system must use the transformed dataset supplied in `DataSet/`. It must not use public IEEE-CIS/Kaggle files to recover outcomes.

## 3. Actors

| Actor | Required capability |
|---|---|
| Fraud analyst | Open a case, inspect evidence, review patterns, and submit or escalate a recommendation |
| Team lead | Review and approve `L1` actions |
| Fraud manager | Review and approve `L2` actions |
| Policy owner | Inspect policy decisions, rule citations, routes, and validation failures |
| System operator | Configure dataset paths, graph connection, model settings, and run batch jobs |
| Hackathon reviewer | Run the system, inspect the graph-backed workflow, and review generated answer files |

## 4. Data Requirements

### DR-01: Input files

The system shall support these supplied files:

- `transactions.csv`
- `identity.csv`
- `closed_cases_history.csv`
- `case_pack.csv`
- `DataSet/README.md`

### DR-02: Immutable source data

Raw input files shall be treated as read-only. Derived mappings, profiles, detector results, graph-load files, and answer files shall be written to separate artifact/output directories.

### DR-03: Dataset integrity

The verification job shall check row counts, required columns, unique transaction IDs, timestamp derivation, channel semantics, known transaction links, and benchmark case references before graph loading or answer generation.

### DR-04: Entity identity

The system shall represent customers, cards, transactions, devices, email domains, billing regions, closed cases, and benchmark cases as distinct entity types. Unresolved transaction-to-card mappings shall remain explicit and shall not be silently inferred.

### DR-05: Time semantics

The system shall use dataset timestamps consistently and shall retrieve historical closed cases only when `closed_at < opened_at` for the investigation being run.

### DR-06: Missing values

Missing values shall mean unknown. The system shall not convert missing identity, address, feature, or mapping values into positive or negative evidence without an explicit rule.

## 5. Functional Requirements

### FR-01: Case intake

The system shall:

- Load all 20 rows from `case_pack.csv`.
- Validate case, transaction, customer, and card identifiers.
- Preserve trigger type, trigger text, opened time, flagged transaction, and supplied risk score.
- Create a unique investigation state for each case.

### FR-02: Evidence profile

For each case, the system shall retrieve:

- Flagged transaction details.
- Customer and card transaction history.
- A bounded 48-hour investigation window.
- Online identity and device information when available.
- Billing regions and email domains.
- Connected customers/cards/devices in the relevant time window.
- Similar closed cases that satisfy temporal constraints.
- Policy and regulatory documents used for interpretation.

Evidence shall include source, reference, entity IDs, timestamp/window, and whether it is direct evidence, model output, customer response, or an assumption.

### FR-03: Pattern detection

The system shall implement deterministic detectors for:

1. Card testing.
2. Card-not-present fraud.
3. Card-not-present fraud from a new device.
4. Out-of-region use.
5. Account takeover.
6. Shared device, region, or recipient-email entities.
7. Undocumented coordinated activity.
8. Structuring below the documented threshold.

Every detector shall return a match/no-match result, evidence IDs, thresholds, time window, confidence inputs, and counter-evidence where available.

### FR-04: Investigation assessment

The system shall record:

- Verdict: `fraud`, `legitimate`, or `uncertain`.
- Fraud probability in the range 0 to 1.
- Selected pattern and undocumented pattern description when applicable.
- Affected transaction IDs and first suspicious transaction.
- Connected card IDs and device profiles.
- Exposure as the sum of absolute affected transaction amounts.
- Evidence count, independence, conflicts, and stop reason.
- Similar prior case IDs.

### FR-05: Policy enforcement

The policy engine shall implement Fraud Policy v1.0 rules R1-R10 and shall be the final authority for actions and routes.

The system shall:

- Use exact action identifiers from `agent.policy.actions.Action`.
- Use exact routes `auto`, `L1`, and `L2`.
- Route actions according to exposure and action type.
- Prevent `BLOCK_ALL_CARDS` unless R10 is satisfied.
- Ensure every action reason cites a policy rule.
- Prevent an LLM or UI input from bypassing policy evaluation.

### FR-06: Evidence requests

The system shall support only these request types:

- `customer_validation`
- `step_up_auth`
- `analyst_info`

Each request shall record type, investigation step, assumed response, timestamp or sequence, and whether the response is simulated.

### FR-07: Initial and final actions

The system shall:

- Persist initial actions before any evidence request.
- Re-evaluate policy after the assumed response.
- Persist final actions.
- Explain changes or record `nothing` when unchanged.
- Keep final SAR status consistent with final `FILE_REPORT` action presence.

### FR-08: Case output

The system shall generate one JSON file at `cases/<case_id>.json` for each benchmark case. Each file shall contain:

- Top-level case ID and execution metadata.
- Complete internal case record.
- Evidence requests.
- Initial and final next-best actions.
- SAR decision and narrative fields.
- Stop reason.

### FR-09: SAR generation

When `FILE_REPORT` is recommended, the system shall generate a standalone narrative containing who, what, when, where, how, and why the activity is suspicious. When no report is recommended, narrative, subjects, amount, and activity dates shall be empty or zero according to the answer contract.

### FR-10: Graph persistence

The system shall write completed case memory to TigerGraph, including case status, verdict, pattern, evidence references, affected transactions, connected entities, actions, and timestamps.

### FR-11: Graph retrieval

The system shall expose bounded graph capabilities through GSQL queries and TigerGraph MCP. Graph results shall be structured summaries, not unbounded raw rows.

### FR-12: GraphRAG

The system shall retrieve both connected graph evidence and relevant text from policy, typology, regulatory, and historical-case documents. Retrieved context shall include provenance and shall be passed to the reasoning layer in a bounded structured format.

### FR-13: Human approval

The system shall display approval route and execution status for each action. It shall not execute `L1` or `L2` actions automatically.

### FR-14: Analyst interface

The UI shall show:

- Case trigger and metadata.
- Investigation status and timeline.
- Evidence claims and source references.
- Customer/card/device/region relationships.
- Pattern matches and counter-evidence.
- Probability, exposure, uncertainty, and stop reason.
- Initial versus final actions and approval routes.
- SAR decision and narrative.
- Validation and data-quality errors.

## 6. Output Contract Requirements

### OR-01: Allowed values

The validator shall enforce all enumerations from `DataSet/README.md`, including statuses, verdicts, patterns, action identifiers, routes, request types, and evidence sources.

### OR-02: Identifier integrity

Every transaction, card, customer, closed-case, benchmark-case, and connected-entity ID in an answer shall exist in the supplied dataset or be explicitly marked as a non-dataset model/reference value where permitted.

### OR-03: Exposure integrity

`exposure_usd` shall equal the sum of absolute amounts for `affected_txn_ids` within the documented floating-point tolerance.

### OR-04: Legitimate-case integrity

For a `legitimate` verdict, affected transaction IDs shall be empty, exposure shall be zero, and SAR filing shall be false.

### OR-05: SAR integrity

`sar.file` shall equal whether `FILE_REPORT` appears in final actions. Filed reports require a narrative, subjects, total amount, and two activity dates.

### OR-06: Action integrity

Every initial and final action shall contain an allowed action, allowed route, and rule-citing reason. If no evidence request exists, final actions shall equal initial actions.

### OR-07: Temporal integrity

Similar prior cases shall be closed before the benchmark case opens. Future case memory shall never be used.

### OR-08: Release gate

No answer file shall be accepted for submission while the validator reports an error.

## 7. Non-functional Requirements

### NFR-01: Explainability

Every material claim and action shall be traceable to evidence and policy rules.

### NFR-02: Determinism

Detectors, exposure calculations, routing, validation, and policy decisions shall be deterministic for the same inputs and configuration.

### NFR-03: Reproducibility

The repository shall provide commands that regenerate artifacts, answer files, validation results, and calibration outputs from a clean environment.

### NFR-04: Safety

The LLM shall not be trusted with raw action execution, route selection, identifier creation, exposure arithmetic, or R10 enforcement.

### NFR-05: Performance

The local batch pipeline shall process all 20 cases in one run. Graph queries shall return bounded evidence briefs suitable for agent context limits.

### NFR-06: Observability

The system shall record tool calls, latency, token usage where applicable, detector version, policy version, graph query provenance, and validation results.

### NFR-07: Data privacy

The system shall keep supplied anonymized data local, avoid external outcome lookup, and document any external regulatory or typology documents used.

### NFR-08: Testability

Unit tests, detector fixtures, policy tests, validator tests, integration tests, and an end-to-end 20-case batch check shall be available.

## 8. Technical Requirements

| Area | Requirement |
|---|---|
| Language | Python 3.11+ recommended; all local scripts shall run from repository root |
| Graph | TigerGraph Savanna or Community Edition |
| Query layer | GSQL queries and TigerGraph graph algorithms |
| Agent tools | TigerGraph MCP client |
| Orchestration | LangGraph or equivalent bounded state machine |
| Retrieval | TigerGraph vector storage/retrieval or approved GraphRAG implementation |
| Policy | Deterministic Python policy engine |
| UI | Analyst-facing web UI with graph/timeline/evidence views |
| Storage | CSV inputs, JSON artifacts, graph case memory, versioned documents |
| Configuration | Environment variables for graph, LLM, MCP, retrieval, and optional Jev settings |

## 9. Security and Governance Requirements

- No public source dataset may be downloaded or used for outcome recovery.
- No hidden benchmark outcomes may enter the benchmark-generation path.
- Customer/analyst responses must be labeled as simulated assumptions.
- Human approval boundaries must be visible in the UI and answer files.
- Model-generated free text must be separated from deterministic evidence and policy outputs.
- All generated artifacts must be reproducible from versioned inputs and configuration.

## 10. Acceptance Criteria

The system meets the baseline requirements when:

1. Dataset verification succeeds.
2. Card mapping completes and unresolved rows remain visible.
3. All seven detector families execute across all 20 cases.
4. HHG-014 exposes the shared Samsung device ring.
5. The policy test suite passes R1-R10 and routing guards.
6. All 20 generated answer files pass validation.
7. At least one case demonstrates changed initial/final actions after an evidence request.
8. At least one case is cleared or remains uncertain without unjustified blocking.
9. Graph schema and load jobs complete without identifier or temporal violations.
10. The UI can show one connected-entity fraud case and one legitimate/ambiguous case.
11. The final repository contains setup instructions, answer files, demo materials, and technical documentation.

## 11. External Dependencies

- TigerGraph Savanna or Community Edition access.
- TigerGraph MCP availability and configuration.
- LLM provider and model credentials for narrative/reasoning only.
- Embedding/vector retrieval provider or TigerGraph vector capability.
- Optional regulatory and typology documents.
- Optional Jev service; the system must run with Jev disabled.

## 12. Out of Scope for Baseline

- Live payment authorization.
- Real customer communications.
- Real SAR submission.
- Production identity and access management.
- Real-time autonomous monitoring beyond the benchmark.
- Recovery of labels from public source data.