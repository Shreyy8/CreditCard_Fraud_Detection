# Project Task Backlog

This is the complete implementation checklist for the benchmark-ready system. Tasks marked `[x]` are already implemented in the repository. Tasks marked `[ ]` remain.

## Phase 0: Project governance and setup

- [x] Read and reconcile the dataset README, project README, PRD, and implementation plan.
- [x] Decide TigerGraph target: TigerGraph Savanna.
- [ ] Create the Savanna workspace and record graph endpoint/database details in local environment configuration.
- [ ] Enable Savanna auto-stop and auto-start to control workspace usage.
- [ ] Create `.env.example` with graph, MCP, LLM, embedding, and feature flags.
- [ ] Add `.gitignore` rules for raw external datasets, secrets, model files, and generated credentials.
- [ ] Add pinned Python dependency file and installation instructions.
- [ ] Add a single documented clean-start command sequence.
- [ ] Define repository conventions for source, artifacts, cases, graph files, documents, and UI.
- [ ] Document the prohibition on public IEEE-CIS/Kaggle outcome recovery.

## Phase 1: Dataset contract and local artifacts

- [x] Verify transaction and identity row counts and required columns.
- [x] Verify timestamp derivation.
- [x] Verify channel/ProductCD consistency.
- [x] Verify unique transaction IDs.
- [x] Verify all case-pack and closed-case transaction links.
- [x] Derive transaction-to-card mappings from known anchors.
- [x] Preserve unresolved card mappings.
- [ ] Add automated verification for every required dataset file.
- [ ] Add machine-readable verification report with pass/fail status.
- [ ] Add artifact provenance metadata and generation timestamps.
- [ ] Add duplicate and null-rate profiling for important fields.
- [ ] Add a data dictionary for all fields used by detectors.
- [ ] Add checks that benchmark cases are chronologically ordered before execution.

## Phase 2: Local evidence engine

- [x] Build local profiles for all benchmark cases.
- [x] Include flagged transaction and customer/card history.
- [x] Include bounded 48-hour windows.
- [x] Include identity/device profile records.
- [x] Include billing regions.
- [x] Include temporally valid similar prior cases.
- [ ] Add evidence provenance objects with source file, row/entity ID, and retrieval timestamp.
- [ ] Add independent-evidence classification.
- [ ] Add explicit counter-evidence generation.
- [ ] Add recurring-charge detection for R7.
- [ ] Add customer history baselines for normal amount, channel, device, region, and email behavior.
- [ ] Add evidence profile versioning.

## Phase 3: Pattern detectors

- [x] Implement detector output contract.
- [x] Implement card-testing detector.
- [x] Implement shared-entity detector.
- [x] Implement CNP burst detector.
- [x] Implement new-device detector.
- [x] Implement out-of-region detector.
- [x] Implement account-takeover signal detector.
- [x] Implement undocumented coordination detector.
- [x] Implement structuring-under-threshold detection.
- [x] Add HHG-014 device-ring test.
- [x] Add negative shared-overlap test.
- [ ] Add card-testing positive and negative fixture tests.
- [ ] Add out-of-region traveler/legitimate fixture tests.
- [ ] Add recurring-charge legitimate fixture tests.
- [ ] Add missing-identity and unresolved-card tests.
- [ ] Add detector threshold configuration rather than hard-coded values.
- [ ] Add detector result ranking and conflict resolution.
- [ ] Review false positives across all 20 generated results.

## Phase 4: Policy engine and decisioning

- [x] Implement exact action and route enums.
- [x] Implement deterministic policy engine.
- [x] Implement R1-R10 logic.
- [x] Implement exposure-dependent routing.
- [x] Implement R10 `BLOCK_ALL_CARDS` guardrail.
- [x] Add policy tests in `test_policy_rules.py`.
- [ ] Install test dependencies and make the full policy suite runnable in clean setup.
- [ ] Add policy result serialization.
- [ ] Add policy version to every answer and graph case.
- [ ] Add action deduplication and stable ordering.
- [ ] Add explicit action execution adapter that rejects L1/L2 execution.
- [ ] Add tests for action conflicts across multiple detector matches.
- [ ] Add tests for recurring-charge R7 precedence.

## Phase 5: Evidence requests and state machine

- [x] Implement simulated customer-validation requests.
- [x] Implement no-reply branch.
- [x] Persist initial and final actions.
- [x] Persist `what_changed`.
- [ ] Add explicit state machine states: trigger, open, gather, detect, assess, request, reassess, recommend, approve, close.
- [ ] Add checkpoint/resume support.
- [ ] Add request policy deciding when more evidence can change the decision.
- [ ] Add step-up authentication simulation.
- [ ] Add analyst-information simulation.
- [ ] Add response provenance and timestamps.
- [ ] Add stop-rule explanation for every terminal state.
- [ ] Add state transition tests.

## Phase 6: Probability calibration and evaluation

- [x] Add dependency-free isotonic calibration utility.
- [x] Add calibration fit CLI.
- [x] Generate closed-case backtest predictions using the local investigator.
- [x] Split fit and holdout data chronologically.
- [x] Rebalance or document prevalence assumptions.
- [x] Report Brier score and reliability tables.
- [x] Compare raw versus calibrated probabilities on untouched holdout data.
- [x] Save calibration provenance and fit slice boundaries.
- [x] Apply calibration only when holdout performance improves.
- [x] Add benchmark-case probability generation after calibration is frozen.
- [x] Add accuracy, calibration, action, SAR, and exposure evaluation reports.

## Phase 7: Answer generation and validation

- [x] Implement answer composer.
- [x] Implement answer schema validator.
- [x] Validate IDs and exposure.
- [x] Validate SAR and final-action consistency.
- [x] Validate action routes and rule citations.
- [x] Generate 20 draft answer files.
- [x] Validate all 20 draft files successfully.
- [x] Add schema version to answer files.
- [ ] Validate connected customer IDs and device references where applicable.
- [x] Validate SAR narrative sentence/content requirements.
- [ ] Validate temporal prior-case references directly from answer metadata.
- [x] Add answer lint output suitable for CI.
- [ ] Review every draft answer manually for unsupported conclusions.
- [ ] Freeze final answer files only after detector and calibration review.

## Phase 8: TigerGraph schema and data loading

- [ ] Create graph schema for Customer, Card, Transaction, DeviceProfile, EmailDomain, BillingRegion, ClosedCase, Case, Evidence, and Document in Savanna.
- [ ] Define primary IDs and attribute types.
- [ ] Define `OWNS`, `MADE`, `FROM_DEVICE`, `PURCHASER_EMAIL`, `BILLED_IN`, `NEXT`, `INVOLVES`, `ON_CARD`, `CONNECTED_TO`, and case-memory edges.
- [ ] Define temporal edge/vertex attributes.
- [ ] Create CSV preparation jobs from local artifacts.
- [ ] Create GSQL loading jobs.
- [ ] Load core Customer/Card/Transaction graph.
- [ ] Load identity/device entities.
- [ ] Load regions and email domains.
- [ ] Load historical closed cases.
- [ ] Load benchmark cases and case memory.
- [ ] Add load-time assertions for counts, IDs, timestamps, and relationships.
- [ ] Add repeatable graph reset/reload command.
- [ ] Compare graph counts with local verification reports.

## Phase 9: GSQL queries and graph algorithms

- [ ] Query customer transaction history.
- [ ] Query card transaction windows.
- [ ] Query online identity/device history.
- [ ] Query billing-region history.
- [ ] Query device neighbors across customers/cards.
- [ ] Query region and email neighbors.
- [ ] Query temporally valid prior cases.
- [ ] Implement card-testing traversal/query.
- [ ] Implement CNP burst query.
- [ ] Implement new-device query.
- [ ] Implement out-of-region query.
- [ ] Implement account-takeover query.
- [ ] Implement shared-entity ring query.
- [ ] Implement undocumented coordination discovery query.
- [ ] Add graph algorithm for connected-component/ring analysis.
- [ ] Return bounded structured evidence briefs from every query.
- [ ] Add query fixtures and compare query output with local detectors.

## Phase 10: TigerGraph MCP and GraphRAG

- [ ] Configure TigerGraph MCP connection.
- [ ] Implement MCP health check.
- [ ] Expose allowlisted graph queries as agent tools.
- [ ] Validate tool arguments and result schemas.
- [ ] Add tool timeout and retry behavior.
- [ ] Log tool calls and graph query provenance.
- [ ] Prepare policy and dataset pattern documents for retrieval.
- [ ] Prepare closed-case notes for retrieval.
- [ ] Prepare permitted regulatory and typology documents.
- [ ] Create Savanna vector embeddings/indexes.
- [ ] Implement hybrid graph-plus-vector retrieval.
- [ ] Add retrieval citations and document section references.
- [ ] Bound retrieved context by token/record limits.
- [ ] Test retrieval on HHG-014 and one legitimate case.

## Phase 11: Agent orchestration and LLM integration

- [ ] Choose LangGraph or equivalent orchestration framework.
- [ ] Define typed investigation state.
- [ ] Implement trigger and case-opening nodes.
- [ ] Implement graph evidence gathering node.
- [ ] Implement deterministic detector node.
- [ ] Implement structured assessment node.
- [ ] Implement evidence-request node.
- [ ] Implement policy-check node.
- [ ] Implement narrative/explanation node.
- [ ] Implement graph case-memory write node.
- [ ] Implement answer serialization node.
- [ ] Add LLM structured-output schema.
- [ ] Restrict LLM context to graph/retrieval briefs.
- [ ] Reject invalid LLM IDs/actions and retry or fall back.
- [ ] Keep policy actions deterministic after LLM output.
- [ ] Add prompt/model/version metadata.
- [ ] Add graceful fallback when LLM, MCP, or optional Jev is unavailable.
- [ ] Keep Jev disabled by default and optional.

## Phase 12: Analyst UI

- [ ] Choose UI framework and application structure.
- [ ] Add case list and case selection.
- [ ] Add case header and trigger panel.
- [ ] Add transaction timeline.
- [ ] Add evidence claims with citations.
- [ ] Add graph relationship visualization.
- [ ] Add pattern detector panel.
- [ ] Add probability/exposure/uncertainty panel.
- [ ] Add initial/final action comparison.
- [ ] Add approval route and execution state.
- [ ] Add evidence-request history.
- [ ] Add SAR decision and narrative view.
- [ ] Add validation/data-quality warning view.
- [ ] Add answer JSON download.
- [ ] Add loading, empty, error, and degraded-mode states.
- [ ] Verify desktop and mobile layout for the demo.

## Phase 13: Testing and quality

- [x] Run detector tests.
- [x] Run investigation and validator tests.
- [x] Run Python compilation checks.
- [ ] Install and run the complete policy test suite.
- [ ] Add dataset verification tests.
- [ ] Add graph load integration tests.
- [ ] Add MCP tool contract tests.
- [ ] Add GraphRAG retrieval tests.
- [ ] Add end-to-end one-case test.
- [ ] Add end-to-end 20-case batch test.
- [ ] Add temporal leakage test suite.
- [ ] Add no-public-data compliance check.
- [ ] Add malformed answer/failure-path tests.
- [ ] Add performance baseline and regression threshold.
- [ ] Add CI workflow for tests, compile, validation, and artifact checks.

## Phase 14: Documentation and submission

- [ ] Update README setup instructions.
- [ ] Document local-only reference pipeline.
- [ ] Document TigerGraph setup and shutdown.
- [ ] Document graph schema and GSQL queries.
- [ ] Document MCP configuration.
- [ ] Document GraphRAG sources and citations.
- [ ] Document policy engine and approval boundaries.
- [ ] Document answer schema and validator.
- [ ] Document calibration methodology.
- [ ] Generate final 20 answer files.
- [ ] Write technical blog post.
- [ ] Create 3-5 minute demo script.
- [ ] Record demo video.
- [ ] Prepare X/LinkedIn post tagging `@TigerGraphDB`.
- [ ] Complete submission checklist.

## Phase 15: Optional innovation

- [ ] Add Jev triage integration behind `JEV_ENABLED`.
- [ ] Add Jev response classification.
- [ ] Add autonomous monitoring over the exam period.
- [ ] Detect new rings outside the 20 benchmark cases.
- [ ] Produce autonomous-monitoring output in a separate folder.
- [ ] Add analyst feedback loop for detector/policy review.

## Current Critical Path

1. Install dependencies and make the complete test suite runnable.
2. Review and improve detector false positives across all 20 cases.
3. Generate temporal backtest predictions and freeze calibration.
4. Finalize the answer schema and manually review generated answers.
5. Build TigerGraph schema and repeatable load jobs.
6. Implement and test bounded GSQL evidence queries.
7. Connect MCP and GraphRAG.
8. Implement the state-machine agent.
9. Build the analyst UI.
10. Run end-to-end validation and prepare submission artifacts.