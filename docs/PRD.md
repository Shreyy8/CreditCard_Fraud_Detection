# Product Requirements Document

## Agentic Fraud Investigation System

**Status:** Draft for implementation  
**Version:** 0.1  
**Date:** 2026-09-22  
**Audience:** Product, engineering, data science, fraud operations, and hackathon reviewers

## 1. Product Summary

Build an agentic fraud-investigation workspace that takes a card-fraud alert, gathers connected evidence from transactions, identity records, prior investigations, and policy documents, then produces an auditable case decision and next-best action.

The product is optimized for the 20-case TigerGraph x Hacker House Goa 2026 benchmark. It must also demonstrate a credible production shape: graph-based investigation, deterministic policy enforcement, controlled evidence requests, temporal case memory, explainable decisions, and human approval for consequential actions.

The product is decision support, not an autonomous banking authority. The agent may execute only actions routed as `auto`; `L1` and `L2` actions are recommendations awaiting human approval.

## 2. Problem

Fraud alerts combine weak and strong signals across disconnected records. An analyst must determine whether the alert is legitimate, identify the scope of possible fraud, find related customers or cards, decide whether more evidence is needed, and select an action that complies with policy.

The current manual workflow has four risks:

- A high model score can be mistaken for a fraud verdict.
- Cross-card relationships, especially shared devices, are difficult to see in tabular data.
- Evidence requests and changing decisions are not consistently recorded.
- Actions may be recommended without a traceable policy rule, approval route, or supporting evidence.

## 3. Goals

### Primary goals

1. Investigate all 20 benchmark cases using only the supplied transformed dataset and permitted documents.
2. Produce one complete, schema-valid answer file per case.
3. Detect documented patterns and surface coordinated undocumented patterns such as device rings and structuring.
4. Generate policy-compliant `initial` and `final` next-best actions with exact action identifiers and approval routes.
5. Make every material conclusion traceable to structured evidence, temporal scope, and a numbered policy rule.
6. Persist closed cases as graph memory so later investigations can retrieve them without temporal leakage.

### Secondary goals

- Provide an analyst-facing investigation view for a compelling end-to-end demo.
- Support backtesting and probability calibration without using hidden benchmark outcomes.
- Make TigerGraph graph traversal, graph algorithms, MCP, and vector retrieval visible in the architecture and demo.

## 4. Non-goals

- Automatically deciding the ground-truth outcome from an unavailable fraud label.
- Reconstructing outcomes from the public IEEE-CIS or Kaggle source files.
- Replacing a human approver for `L1` or `L2` actions.
- Building a complete payment authorization or case-management platform.
- Treating an LLM as the source of truth for policy, identifiers, calculations, or graph relationships.
- Supporting arbitrary external production data in the benchmark MVP.

## 5. Users and User Needs

### Fraud analyst

Needs a compact evidence brief, related-entity view, pattern assessment, uncertainty, and a defensible recommendation that can be reviewed quickly.

### Fraud team lead or manager

Needs to see why an action requires approval, what evidence supports it, exposure, affected cards, and whether the recommendation changed after an evidence request.

### Model and policy owner

Needs reproducible policy evaluation, validation failures, calibration metrics, temporal backtesting, and an audit trail of model and agent inputs.

### Hackathon reviewer

Needs to see graph-native investigation, agentic tool use, a clear human-in-the-loop boundary, and a complete result for representative cases.

## 6. Product Principles

- **Evidence before narrative:** graph queries and deterministic detectors produce the facts; the LLM summarizes and explains them.
- **Risk score is a trigger, not a verdict:** the system must be able to clear alerts.
- **Policy is executable:** the policy engine is the final authority over actions and routes.
- **Temporal honesty:** only closed cases with `closed_at < case.opened_at` may inform a benchmark case.
- **Uncertainty is visible:** probability, evidence count, evidence independence, conflicts, and stop reason are first-class fields.
- **Unknown stays unknown:** sparse values and unresolved card mappings must not be silently converted into facts.
- **Every claim is inspectable:** IDs, timestamps, source records, and rule citations must be available to the reviewer.

## 7. MVP Scope

### In scope

- Dataset verification and immutable input handling.
- Derived transaction-to-card mapping with explicit unresolved rows.
- Local evidence profiles for all benchmark cases.
- Pattern detectors for card testing, CNP activity, new device, out-of-region use, account takeover signals, shared entities, and undocumented coordination.
- Deterministic policy engine implementing R1-R10 and exact action routing.
- Answer schema validation, ID validation, exposure validation, SAR/action consistency, and temporal leakage checks.
- One complete local investigation path, then execution across all 20 cases.
- TigerGraph schema, load jobs, GSQL pattern queries, graph algorithms, and MCP integration.
- GraphRAG retrieval for policy, closed-case notes, typologies, and regulatory context.
- Analyst UI showing evidence, graph connections, timeline, decision, policy actions, and audit trail.

### Post-MVP / innovation scope

- Optional Jev triage and response classification.
- Autonomous monitoring beyond the 20 benchmark cases.
- Live customer or authentication integrations.
- Production deployment, identity access management, and operational SLAs.

## 8. Core User Journey

1. **Select a case:** analyst opens a case-pack alert and sees trigger, flagged transaction, customer, card, timestamp, and initial risk score.
2. **Open investigation:** system creates an investigation state and records the trigger without treating it as a verdict.
3. **Gather evidence:** agent retrieves customer/card history, transaction window, identity/device profile, billing regions, connected entities, and temporally valid prior cases.
4. **Detect patterns:** deterministic detectors return structured matches, counter-evidence, confidence inputs, and source IDs.
5. **Assess:** the agent records verdict, fraud probability, exposure, affected transactions, uncertainty, and whether evidence is independent or conflicting.
6. **Recommend initial actions:** policy engine evaluates the evidence before any request is issued. These actions are persisted as `initial`.
7. **Request evidence when needed:** only policy-approved evidence requests may be simulated. The request and assumed response are recorded.
8. **Reassess:** new evidence is added to the timeline and the policy engine produces `final` actions plus `what_changed`.
9. **Review and approve:** auto actions may execute; `L1` and `L2` actions wait for the appropriate human route.
10. **Close and remember:** system writes the case, evidence, decision, and approved outcome to graph memory and exports the answer JSON.

## 9. Functional Requirements

### FR-1: Case intake

- Accept every row in `case_pack.csv`.
- Display `case_id`, trigger type/text, opened time, flagged transaction, customer, card, and supplied risk score.
- Reject unknown transaction, customer, card, or case identifiers before investigation starts.

### FR-2: Evidence retrieval

The system must retrieve and label:

- Flagged transaction details and nearby transactions.
- Customer and card history before the case opening time.
- Online identity and device profile when available.
- Billing regions, email domains, and shared entities.
- Similar closed cases with valid temporal boundaries.
- Policy and regulatory passages used to support narrative or interpretation.

The evidence response must be structured and bounded. Raw unbounded CSV rows must not be passed directly to the LLM.

### FR-3: Pattern detection

Each detector must return a pattern identifier or an explicit no-match, source transaction IDs, time window, relevant thresholds, and counter-evidence where available.

Required detectors:

- `card_testing`: at least three small online authorizations within one hour followed by a larger purchase.
- `cnp`: unusual online activity or burst relative to the card/customer history.
- `cnp_new_device`: CNP evidence plus a device marked new for the account.
- `out_of_region`: in-person activity in a new region while normal home activity continues.
- `account_takeover`: mixed-channel and identity/match anomalies inconsistent with history.
- `shared_entity`: multiple cards or customers connected by device, region, or recipient email in a relevant window.
- `undocumented`: coordinated or repeated abuse that does not fit a documented pattern.

### FR-4: Decision and exposure

- Record `fraud`, `legitimate`, or `uncertain`.
- Record a probability from 0 to 1 with an explanation of the evidence supporting calibration.
- Calculate exposure from the selected affected transactions using dataset amounts and an explicit tolerance policy.
- List affected transaction IDs, connected cards, connected devices, and similar prior case IDs.
- Preserve unresolved mappings as uncertainty rather than assigning a card identity by guesswork.

### FR-5: Policy-controlled actions

- Evaluate all recommendations through `agent.policy`.
- Use only exact identifiers from `Action` and `Route`.
- Require every recommendation reason to cite its rule, such as `R5:` or `R9:`.
- Enforce routing: `auto`, `L1`, or `L2`.
- Enforce R10 before allowing `BLOCK_ALL_CARDS`.
- Ensure `FILE_REPORT` is consistent with the SAR decision.

### FR-6: Evidence requests and action evolution

- Record `initial` actions before requesting evidence.
- Record request type, requested-at time, simulated response, assumption, and source.
- Record `final` actions after the response.
- Set `what_changed` to a specific explanation or `nothing` when the recommendations are unchanged.
- Stop when a policy stop rule is met or when no permitted evidence request can materially reduce uncertainty.

### FR-7: Case and SAR output

- Generate one JSON file per benchmark case under `cases/<case_id>.json`.
- Include a complete internal case record and a standalone SAR narrative when required.
- Write the closed case to graph memory with evidence and timestamps.
- Validate every ID and required field before output is accepted.

### FR-8: Analyst workspace

The UI must show, without requiring users to inspect logs:

- Case header and trigger.
- Evidence timeline and source citations.
- Customer/card/device/region relationship graph.
- Pattern matches and counter-evidence.
- Probability, exposure, and uncertainty indicators.
- Initial versus final actions, route, rule citation, and execution status.
- SAR decision and narrative.
- Validation errors and data-quality warnings.

## 10. Output Contract

The answer schema is the product's external contract. At minimum it must contain:

- `case`: case ID, status, verdict, probability, pattern, summary, evidence, affected transactions, exposure, connected entities, and similar prior cases.
- `sar`: `file` decision and narrative when applicable.
- `next_best_action`: `initial`, `final`, and `what_changed`; each recommendation contains exact action, route, reason, and execution state.
- `evidence_requests`: request, timing, simulated response, and assumptions.

The validator is a release gate. A case cannot be marked complete if schema, identifier, calculation, temporal, policy, or SAR consistency validation fails.

## 11. Non-functional Requirements

### Auditability

Every output claim must link to evidence IDs or a clearly labeled model synthesis. Store detector version, policy version, prompt/model metadata, timestamps, and graph query provenance.

### Safety and governance

The LLM cannot directly execute actions, change routes, invent IDs, or bypass R10. Human approval is mandatory for `L1` and `L2` actions.

### Reproducibility

The same dataset, configuration, and detector/policy versions should produce stable structured results. Nondeterministic narrative generation must not change policy actions.

### Performance target

The local pipeline should process all 20 cases in one repeatable batch run. Graph retrieval should return a bounded evidence brief suitable for one agent turn; exact production latency is deferred until TigerGraph deployment.

### Data handling

Use only the supplied transformed dataset and explicitly documented external documents. Never retrieve outcomes from the public source dataset. Keep raw inputs immutable.

## 12. Success Metrics and Acceptance Criteria

### Release acceptance

- All 20 cases produce schema-valid JSON files.
- All answer IDs exist in the supplied dataset.
- No temporally invalid closed case is retrieved.
- All policy tests pass, including R1-R10, routes, stop behavior, and R10.
- `FILE_REPORT` and SAR decisions agree for every case.
- `initial` and `final` actions are present, even when identical.
- Every action reason cites a valid policy rule.
- Exposure is reproducible from listed transaction IDs within the documented amount tolerance.
- At least one demo case shows a connected-entity investigation; HHG-014 is the primary candidate.
- At least one legitimate case is cleared without an unjustified block.

### Quality metrics

- Pattern and verdict accuracy against the hidden benchmark key.
- Calibration error for `fraud_probability`.
- Correct action and approval-route rate.
- Correct case-only versus case-plus-report rate.
- Percentage of conclusions with valid evidence citations.
- Percentage of investigations completed without unresolved validation errors.
- Time from case open to analyst-ready recommendation.

## 13. Delivery Plan

### Phase 1: Local investigation foundation

- Finish pattern detectors and answer-schema validator.
- Complete one end-to-end local investigation for HHG-014.
- Add focused detector tests and inspect false positives.

### Phase 2: Benchmark generation

- Run all 20 cases chronologically.
- Review legitimate, high-risk, and undocumented cases.
- Add backtesting and probability calibration using only historical closed cases.

### Phase 3: Graph implementation

- Load Customer, Card, Transaction, ClosedCase, DeviceProfile, EmailDomain, and BillingRegion.
- Add temporal `NEXT` edges and graph pattern queries.
- Compare local detector results with graph query results.

### Phase 4: Agent and retrieval

- Connect TigerGraph MCP.
- Add structured GraphRAG retrieval for policy, closed cases, and regulatory material.
- Implement the bounded state machine and checkpointing.
- Keep LLM synthesis behind validated structured inputs.

### Phase 5: UI and submission

- Build the analyst investigation view.
- Prepare a 3-5 minute demo around HHG-014 and one legitimate case.
- Produce repository setup documentation, answer files, technical write-up, and submission checklist.

## 14. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Ambiguous card mapping | Incorrect connected-card conclusions | Anchor known links, expose unresolved rows, never infer silently |
| Benchmark leakage | Disqualification or invalid results | Enforce temporal filters and prohibit public source files |
| LLM invents evidence or actions | Unsafe and unscorable output | Structured tool results, schema validation, deterministic policy gate |
| High closed-case fraud base rate biases decisions | Excessive blocking and poor calibration | Use benchmark prior only as a documented hypothesis; calibrate on held-out history |
| Sparse identity/features | False certainty | Treat null as unknown and expose counter-evidence |
| Graph/MCP setup delays | Delivery risk | Maintain a local reference implementation and integrate graph after behavior is testable |
| UI consumes build time | Weak core accuracy | Prioritize answer files, policy, detectors, and validation before polish |

## 15. Open Decisions

- Which TigerGraph deployment target will be used for the final demo: Savanna or Community Edition?
- Which LLM and embedding model are available within the hackathon environment?
- Which evidence-request response simulation policy will be used consistently across cases?
- What probability calibration method will be accepted for the benchmark run?
- Which UI framework best fits the available time and deployment environment?

## 16. Definition of Done

The MVP is done when a reviewer can select a benchmark case, see the graph-backed investigation and evidence timeline, inspect the detector outputs and uncertainty, compare initial and final recommendations, verify policy routes and rule citations, and download a schema-valid answer file. The same run must generate all 20 case files with no validation failures.