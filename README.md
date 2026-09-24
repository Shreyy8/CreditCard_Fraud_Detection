# Agentic Fraud Investigation Agent (TigerGraph)

An AI agent that investigates card-fraud alerts, opens and progresses cases, decides when it has enough evidence, requests more evidence through policy-approved actions, and recommends the next best action with an approval route. Every decision is explained and traced back to evidence and to a numbered policy rule.

Built for the **TigerGraph × Hacker House Goa 2026 Agentic Fraud Investigation Hackathon**, on the IEEE-CIS (Vesta) dataset.

**Sources of truth, in order:** (1) the dataset `README.md` (task, Fraud Policy v1.0, answer format, the 20 cases); (2) the hackathon brief PDF (required components, submission items, judging). Where this file disagrees with either, they win.

---

## Table of contents

1. [The task in one page](#1-the-task-in-one-page)
2. [Constraints checklist](#2-constraints-checklist)
3. [Dataset facts](#3-dataset-facts)
4. [Architecture](#4-architecture)
5. [Graph schema](#5-graph-schema)
6. [Repository layout](#6-repository-layout)
7. [Prerequisites and setup](#7-prerequisites-and-setup)
8. [Loading the data](#8-loading-the-data)
9. [Agent workflow and tools](#9-agent-workflow-and-tools)
10. [Policy engine (Fraud Policy v1.0)](#10-policy-engine-fraud-policy-v10)
11. [Case memory and leakage rules](#11-case-memory-and-leakage-rules)
12. [Simulated evidence requests](#12-simulated-evidence-requests)
13. [Answer files and validator](#13-answer-files-and-validator)
14. [Evaluation and backtesting](#14-evaluation-and-backtesting)
15. [User interface](#15-user-interface)
16. [Optional: autonomous monitoring](#16-optional-autonomous-monitoring)
17. [Build order](#17-build-order)
18. [Submission checklist](#18-submission-checklist)
19. [Troubleshooting](#19-troubleshooting)
20. [Links](#20-links)

---

## 1. The task in one page

For each of the **20 cases in `case_pack.csv`** (all from Nov-Dec 2016), the agent investigates using the graph and the closed-case history, then produces **one JSON answer file** with three parts:

| Part | What | Notes |
|---|---|---|
| **1. Case** | Internal investigation record: status, verdict, fraud probability, pattern, evidence, affected transactions, connected cards/devices, exposure, prior cases retrieved | Also **written into the graph** as case memory |
| **2. SAR** | Suspicious Activity Report narrative, **only when policy calls for it** | Must stand alone: who, what, when, where, how, why suspicious |
| **3. Next best action** | Recommended actions with approval route, **`initial`** (before any requested evidence) and **`final`** (after) | The recommendation may change. Show that it did, and why |

Answers are scored against a hidden answer key. Things that are scored: pattern, verdict, calibration of `fraud_probability`, affected transactions and exposure, connected cards/devices, SAR decision, action correctness and routes, handling of ambiguity, undocumented-pattern discovery, and explanation quality.

Core flow: **Trigger → Investigate → Gather evidence → Assess uncertainty → Gather more evidence if needed → Take next actions → Explain → Update case memory.**

Design principles:

| Principle | How |
|---|---|
| Graph does the analysis, LLM does the reasoning | GSQL queries and TigerGraph algorithms produce evidence. The LLM synthesizes, selects tools and explains. It never replaces graph analysis |
| Policy is enforced in code | A deterministic policy engine implements R1-R10, approval routing, case/SAR criteria and stopping rules. The LLM cannot emit an action or route the policy forbids |
| Uncertainty is computed | Probability and evidence independence drive the stop or continue decision (Policy section 6) |
| Half the cases are legitimate | The agent must be able to clear cases. Blocking everything scores badly |

---

## 2. Constraints checklist

### 2.1 Required components (hackathon brief)

| # | Requirement | Where | Done |
|---|---|---|---|
| 1 | TigerGraph **Savanna** or **Community Edition** for graph **and vector** storage/retrieval | `graph/`, `rag/` | [ ] |
| 1a | If Savanna: **auto-stop and auto-start enabled** | Savanna console | [ ] |
| 2 | GSQL and TigerGraph graph algorithms for traversal, pattern detection, relationship analysis | `graph/queries/` | [ ] |
| 3 | TigerGraph MCP exposes graph capabilities to the agent | `agent/tools/mcp_client.py` | [ ] |
| 4 | GraphRAG: connected graph evidence **plus** documents (policy, typologies, regulations), passed to the LLM as structured context, not raw rows | `rag/` | [ ] |
| 5 | UI showing investigation, case progression, evidence, uncertainty, recommendations, next actions | `ui/` | [ ] |

### 2.2 Agent behaviors (brief)

Trigger from signal, customer report or analyst; gather evidence from graph, transactions, device/identity, account behavior, prior cases; identify pattern and risk; create and progress a case; use case memory; gather more evidence via controlled actions; recommend or execute actions within permissions; stop when enough evidence exists; explain reasoning. Each is mapped to a module in [section 9](#9-agent-workflow-and-tools).

### 2.3 Dataset README rules

| Rule | Enforcement |
|---|---|
| **Do not use the original public IEEE-CIS / Kaggle files to recover outcomes.** IDs, times and amounts were transformed. Doing so is **disqualification** | Never download or reference the public files. Add them to `.gitignore` and code review. Only use files in `data/raw/` |
| **Every ID in every answer file must exist in this dataset.** Made-up IDs score zero | Validator checks every ID against the graph ([section 13](#13-answer-files-and-validator)) |
| Use the provided data as the common benchmark. Extending it with your own data is allowed | Extra data lives in `data/external/` and is documented |
| Action names and approval routes must use the **exact identifiers** in the policy | Enum-typed in `agent/policy/actions.py` |
| Customer/analyst replies are **not provided**. Simulate them and record the assumption in `evidence_requests` | [Section 12](#12-simulated-evidence-requests) |
| Use V/C/D/M/id columns as signals, but **say so in evidence** and do not pretend to know what `V127` means | Evidence templates label these as "unnamed model feature" |
| `sar.file` must agree with whether `FILE_REPORT` is in `final` | Validator |
| Missing fields score zero for that part | Schema validation on every file |
| One file per case, named `<case_id>.json`, in a folder called **`cases/`** in the repo | `cases/` (generated) |

### 2.3b Policy constraints (Fraud Policy v1.0)

Summarized here, detailed in [section 10](#10-policy-engine-fraud-policy-v10): only `auto` actions may be executed by the agent; `L1`/`L2` actions are recommended and wait for a human; never `BLOCK_ALL_CARDS` unless R10 holds; a case is not a report (3a); stop rules (6); every recommendation cites its rule number (7).

### 2.4 Submission deliverables

- [ ] Working agent
- [ ] GitHub repository with setup instructions
- [ ] **20 answer files** in `cases/`, each also written to the graph
- [ ] 3-5 minute demo video, end to end
- [ ] Technical blog post: what you built, architecture, how TigerGraph is used, agentic capabilities, what you learned, what you would improve
- [ ] X or LinkedIn post about the build, with a link to the blog or demo, **tagging @TigerGraphDB**
- [ ] Optional: separate folder of autonomous-monitoring output (counts toward Innovation only)

### 2.5 Judging criteria

| Criterion | Weight | Where we invest |
|---|---|---|
| Investigation accuracy | 25% | Pattern queries, ring detection, undocumented-pattern discovery, backtest |
| Next best action | 25% | Policy engine, `initial` vs `final`, uncertainty handling |
| Case summary and explainability | 10% | Case record, evidence citations, rule numbers |
| Agentic design and engineering | 15% | State machine, tools, memory, permissions, tests |
| Innovation | 15% | Graph-plus-vector memory, ring detection, undocumented patterns, autonomous monitoring |
| Demo quality | 10% | UI, demo script |

---

## 3. Dataset facts

Files in `data/raw/`:

| File | Contents |
|---|---|
| `transactions.csv` | 590,742 transactions (about 708 MB). All 393 original Vesta columns plus `customer_id`, `ts`, `channel`, `risk_score`. **No fraud flag** |
| `identity.csv` | 144,432 identity records, 41 original columns, joined on `TransactionID`. Online transactions only |
| `closed_cases_history.csv` | 5,565 closed investigations, Jul-Oct 2016: 4,665 `confirmed_fraud`, 900 `cleared` |
| `case_pack.csv` | The 20 exam cases: `case_id, opened_at, trigger_type, trigger_text, flagged_txn_id, card_id, customer_id, risk_score` |
| `README.md` | Task, patterns, regulatory links, Fraud Policy v1.0, answer format |

ID formats:

| Entity | Format | Example |
|---|---|---|
| Customer | `C#####` | `C12382` |
| Card | `C#####-K#` | `C12382-K1` (**not a column in `transactions.csv`**, see below) |
| Transaction | integer `TransactionID` | `3514030` (the README's `T0412877` is illustrative. Use real IDs) |
| Closed case | `CC-####` | `CC-2649` |
| Benchmark case | `HHG-###` | `HHG-001` |

Key semantics:

- `channel`: `in_person` (ProductCD `W`, no identity record) or `online` (other ProductCDs, identity record present).
- `addr1` = billing region code, `addr2` = country code (87 is home).
- **Device profile** = `DeviceInfo + id_30 (OS) + id_31 (browser) + id_33 (screen)`. `id_15` is `New` / `Found` / `Unknown`. `id_23` is the proxy type.
- `risk_score` is an **input, not an answer**. Above 0.7 most flagged transactions turn out legitimate, and some fraud scores near zero.
- The `risk_score` on trigger types is filled only for `risk_score` triggers.
- Transaction time: `ts` from 2016-07-02 to 2016-12-31.

### What the `transactions.csv` header and sample rows confirm

(From the header and the first 13 rows only. Re-verify on the full file with `make verify-load`.)

- **397 columns:** the 393 Vesta columns in original order (`TransactionID, TransactionDT, TransactionAmt, ProductCD, card1-card6, addr1, addr2, dist1, dist2, P_emaildomain, R_emaildomain, C1-C14, D1-D15, M1-M9, V1-V339`), then the four added columns `customer_id, ts, channel, risk_score` **at the end**. Address columns by header name in load jobs, never by position.
- **`ts` = 2016-07-02 00:00:00 + `TransactionDT` seconds** (141 → 00:02:21, 505 → 00:08:25). Use this as a load-time assertion.
- **`channel`** matches the README: `W` rows are `in_person`; `C`, `H` (and other codes) are `online`.
- **There is no `card_id` column.** IDs like `C12382-K1` appear only in `closed_cases_history.csv` and `case_pack.csv`. In the sample each customer maps to a single `card1` value (C11919 ↔ 22374, C07867 ↔ 22006), which fits "about 13,500 customers" and suggests `customer_id` is a relabeled `card1`. The `-K#` suffix most likely distinguishes different `card2-card6` combinations within a customer. **This is a hypothesis.** Derive and verify it against the known card IDs before loading (section 8).
- **ID-like fields are floats** (`addr1 = 299.0`, `card2 = 399.0`), and the trigger texts use the same form ("billing region 444.0"). Normalize `BillingRegion` IDs in one place and keep the original string for quoting.
- **Only `W` rows have `addr1`/`addr2` in the sample.** Online rows (C, H) leave them blank. If this holds on the full file, out-of-region evidence comes from in-person rows and online rows rely on device, email and behavior signals. Verify.
- **Data are sparse.** Most `V` values, and many `D`, `M` and email fields, are empty. Null means unknown, not zero.
- **Amounts and times carry small disguise offsets** (dataset README), and values carry float noise (`17051.990234375`). Use tolerances, not exact equality, for "same amount" logic (R7 recurring, structuring under $500). Example: 3000003 and 3000004 are the same card, $83.78 and $83.79, 88 seconds apart.

### What profiling the supplied files showed

(From `closed_cases_history.csv`, `identity.csv` and `case_pack.csv`. Re-verify after loading. Treat these as hypotheses for the agent to test against the graph, **not as hard-coded rules**.)

- **Closed-case pattern mix:** `card_not_present_fraud` 1,404; `account_takeover` 1,205; `card_not_present_new_device` 1,076; `out_of_region_use` 955; `none` (cleared) 900; `card_testing` only 16; `undocumented` 9.
- **Cleared cases (900)** fall into three reasons: traveler confirmed the billing region (716), new phone confirmed (158), unusual-but-intended amount (26). Their closed actions are `VERIFY_WITH_CUSTOMER|CLOSE_NO_FRAUD`.
- **Confirmed fraud** actions are `CREATE_CASE|BLOCK_CARD`, plus `FILE_REPORT` on 397 cases. Report rates by pattern differ sharply: account takeover 187 of 1,205, out of region 124 of 955, new device 56 of 1,076, card testing 7 of 16, plain CNP 14 of 1,404, undocumented 9 of 9.
- **Only four closed cases list `connected_card_ids`, and they are all the undocumented ones.** Two undocumented sub-patterns appear:
  1. A **device ring**: a Samsung SM-G935F on Chrome for Android behind an anonymous proxy, a device never seen on the account, shared by many cardholders (each note says two other cardholders reported it that month; the connected-card lists are long).
  2. **Structuring under a threshold**: four online purchases within forty minutes, each just under $500.
- **Case-pack flagged transactions:** 11 risk-score, 8 customer-report, 1 analyst-request trigger. HHG-014 (analyst request about "several cards ... same unusual device profile") flagged transaction has device `SM-G935F Build/NRD90M`, `id_15 = New`, `IP_PROXY:ANONYMOUS`, which matches undocumented sub-pattern 1. It is a ring-discovery case.
- Closed history is 84% fraud; the benchmark is described as **about half legitimate**. Do not let the closed-case base rate set the agent's prior.
- The latest closed case closes 2016-11-06; the earliest benchmark case opens 2016-11-12.

---

## 4. Architecture

```
                         ┌──────────────────────────────┐
   Trigger ─────────────▶│        LangGraph Agent        │
 (score/report/analyst)  │  state machine, checkpointed  │
                         └───────┬───────────┬──────────┘
                                 │           │
              tool calls (MCP)   │           │  structured brief
                                 ▼           ▼
                    ┌────────────────┐   ┌─────────────────┐
                    │ TigerGraph MCP │   │   LLM (reason,  │
                    │  (GSQL tools)  │   │ select, explain)│
                    └───────┬────────┘   └────────▲────────┘
                            ▼                     │
     ┌──────────────────────────────────────────────┴──────┐
     │                    TigerGraph                        │
     │  Customer · Card · Transaction · DeviceProfile ·     │
     │  EmailDomain · BillingRegion · ClosedCase · Case     │
     │  Vector indexes: closed-case notes, policy,          │
     │  pattern text, regulatory chunks                     │
     └─────────────────────────────────────────────────────┘
                            ▲
                            │ every proposed action
                    ┌───────┴────────┐        ┌──────────────────┐
                    │ Policy engine  │───────▶│ auto: executed    │
                    │ (deterministic)│        │ L1/L2: approval Q │
                    └────────────────┘        └──────────────────┘
```

Agent state machine (LangGraph, or a custom equivalent):

```
trigger → [triage: Jev] → open_case → gather_evidence → [pattern_prescreen: Jev] → match_patterns (LLM)
   → assess (p, evidence count, independence)
   ├─ stop rule met ───────▶ recommend → policy_check → explain (LLM) → write_case_to_graph
   └─ not met, policy allows a request
          → initial actions recorded → request_evidence → (simulated response) → [response_classify: Jev]
          → re-assess → final actions → explain (LLM) → write_case_to_graph
```

**Optional: Jev (TypeSafe AI) as a fast triage layer.** Jev is a "System One" model (launched Sept 2026) that returns typed decisions with calibrated probabilities instead of text — no reasoning, no narrative, just a label and a confidence from a fixed option set. It is not a substitute for the LLM anywhere the output is scored on explanation or calibration of the *final* verdict; it sits **before** the expensive reasoning steps, to decide what deserves full investigation. Three optional insertion points, each a thin wrapper in `agent/tools/jev_client.py` that degrades gracefully to a rule-based fallback if Jev is unavailable:

| Node | Decision | Options | Why Jev here, not the LLM |
|---|---|---|---|
| `triage` (after trigger) | How urgent/deep should this investigation be | `investigate_now \| monitor \| low_priority` | Runs on every trigger; cheap enough to also run continuously in `autonomous/` monitoring over the full exam period |
| `pattern_prescreen` (after evidence gather) | Which of the 5 documented patterns are plausible enough to run full detectors and the LLM match | subset of `{card_testing, cnp, cnp_new_device, out_of_region, ato, undocumented}` | Narrows which GSQL pattern queries and LLM calls actually run per case |
| `response_classify` (after a simulated evidence reply) | How to read the reply | `confirmed \| denied \| no_response` | A closed classification the policy engine (R2/R3/R4) consumes directly |

Hard boundaries (do not move past these into Jev):

- **Final `verdict`, `fraud_probability`, `pattern` in the case record** stay with the LLM — they are graded on calibration and must be explainable, and Jev returns no text at all.
- **`evidence[].claim`, `case.summary`, `sar.narrative`, and every `reason` field** stay with the LLM — free text.
- **Policy actions and routes** stay in deterministic `agent/policy/` code regardless of what proposed them.
- Jev's own outputs (label + probability) are logged as an `evidence[]` item with `source: "model"` like any other input, never presented as a policy decision on their own.

Because Jev is in early access, treat it as **optional and additive**: verify current API availability and docs before building on it, keep `JEV_ENABLED` in `.env`, and make sure the agent runs correctly with it off. This is an Innovation-criterion addition, not something the core pipeline depends on.

Rules of the loop:

- **`initial` actions are recorded before any evidence request is issued**, and `final` after the response. If no request is made, `final` equals `initial` and `what_changed` is `"nothing"`.
- Evidence requests are limited to the three policy-allowed types and are logged as actions.
- The loop is bounded. If still uncertain and exposed above $500, escalate (R8) instead of guessing.
- Stop rules follow Policy section 6 exactly ([section 10.5](#105-stopping-rules)).
- Instrument every case: `tool_calls`, `tokens`, `latency_s` are required output fields.

---

## 5. Graph schema

Start from the dataset's suggested schema, then adapt.

**Vertices:** `Customer`, `Card`, `Transaction`, `DeviceProfile`, `EmailDomain`, `BillingRegion`, `ClosedCase`, plus the agent's own `Case`, `Finding`, `Evidence`, `AgentAction` (or fold into `Case` attributes), and knowledge vertices `PolicyChunk`, `PatternDoc`, `RegulationChunk`.

**Edges:**

| Edge | Notes |
|---|---|
| `Customer -OWNS-> Card` | |
| `Card -MADE-> Transaction` | |
| `Transaction -FROM_DEVICE-> DeviceProfile` | online only |
| `Transaction -PURCHASER_EMAIL-> EmailDomain` | also consider `R_emaildomain` |
| `Transaction -BILLED_IN-> BillingRegion` | from `addr1` |
| `Transaction -NEXT-> Transaction` | ordered by `ts` within a card |
| `ClosedCase -INVOLVES-> Transaction`, `-ON_CARD-> Card`, `-CONNECTED_TO-> Card` | from `txn_ids`, `card_id`, `connected_card_ids` (pipe-separated) |
| `Case -ON_CARD-> Card`, `-INVOLVES-> Transaction`, `-USED_DEVICE-> DeviceProfile`, `-SIMILAR_TO-> ClosedCase` | agent-written |

**Design notes:**

- **393 transaction columns.** Keep every original column available. Suggested: core fields (`TransactionAmt`, `ProductCD`, `card1-6`, `addr1/2`, `dist1/2`, email domains, `ts`, `channel`, `risk_score`) plus `C1-C14`, `D1-D15`, `M1-M9` as typed attributes, and `V1-V339` as a compact list or JSON attribute (or a Parquet sidecar keyed by `TransactionID`). Most `V` values are null in the sample, so store only non-null values (for example a JSON map). Confirm against Savanna memory limits before committing to one layout.
- `Card` vertices are created from the **derived** `card_id` (section 8), not from a source column.
- `DeviceProfile` key = normalized `DeviceInfo | id_30 | id_31 | id_33`. Store proxy type (`id_23`) and `id_15` on the **Transaction -FROM_DEVICE-> edge** (or the transaction), because "New for this account" is a per-account property.
- Tag `ClosedCase` with `opened_at` and `closed_at`, and every agent `Case` with `opened_at` and `source = 'agent'`, so leakage checks are trivial.
- Store `outcome` only on `ClosedCase`. **Never create a fraud label on Transaction.** The only ground truth is closed cases.
- Vector attributes: `ClosedCase.notes_embedding`, `PolicyChunk.embedding`, `RegulationChunk.embedding`, `Case.summary_embedding`.

---

## 6. Repository layout

```
.
├── README.md
├── .env.example
├── .gitignore                   # data/raw, .env, any Kaggle files
├── requirements.txt
├── Makefile
├── data/
│   ├── raw/                     # transactions.csv, identity.csv, closed_cases_history.csv, case_pack.csv
│   └── external/                # optional extensions (documented)
├── scripts/
│   └── derive_card_ids.py       # TransactionID → card_id, verified against closed cases and case pack
├── graph/
│   ├── schema/schema.gsql
│   ├── load/load_jobs.gsql
│   ├── queries/
│   │   ├── card_window.gsql            # card activity in a time window (velocity, amounts, ProductCD)
│   │   ├── card_baseline.gsql          # customer/card history: regions, devices, amounts, products
│   │   ├── device_neighbors.gsql       # cards/customers sharing a device profile in a window
│   │   ├── region_cluster.gsql         # cards sharing a new billing region in a window
│   │   ├── email_neighbors.gsql
│   │   ├── recurring_pattern.gsql      # R7 check: same amount/product/email monthly
│   │   ├── similar_closed_cases.gsql   # Jaccard/cosine + vector search
│   │   ├── communities.gsql            # WCC/Louvain over card-device(-region) graph
│   │   ├── patterns/                   # detectors: card_testing, cnp, cnp_new_device, out_of_region, ato
│   │   └── discovery/                  # structuring under thresholds, proxy device rings, ...
│   └── install.sh
├── rag/
│   ├── ingest_docs.py           # policy, pattern text, regulatory docs → chunks → embeddings
│   ├── ingest_closed_cases.py   # analyst_notes → embeddings
│   └── retriever.py             # subgraph + linked docs + similar cases → structured brief
├── agent/
│   ├── graph.py                 # state machine
│   ├── state.py
│   ├── triggers.py              # risk_score / customer_report / analyst_request
│   ├── case.py                  # case lifecycle, decision log, graph write-back
│   ├── assess.py                # probability, evidence independence, stop rules
│   ├── nodes/
│   ├── tools/                   # MCP client + tool wrappers (counts tool_calls)
│   │   ├── cache.py             # memoized graph reads + parallel first-round evidence fetch
│   │   └── jev_client.py        # optional System One triage calls (JEV_ENABLED), rule-based fallback
│   ├── policy/
│   │   ├── actions.py           # exact action identifiers and routes
│   │   ├── rules.py             # R1-R10 as code
│   │   ├── reporting.py         # case/SAR criteria (3a)
│   │   └── router.py            # approval routing
│   ├── memory/                  # retrieval with temporal filters
│   └── simulators/              # customer, step-up, analyst replies
├── ui/app.py
├── cases/                       # the 20 answer files (generated): HHG-001.json ... HHG-020.json
├── autonomous/                  # optional monitoring output (separate from cases/)
├── eval/
│   ├── backtest.py
│   ├── calibrate.py             # isotonic calibration of fraud_probability, held-out Brier score
│   ├── metrics.py               # accuracy, calibration (Brier), action/route accuracy
│   ├── validate_answers.py
│   └── run_benchmark.py
├── tests/
│   ├── test_policy_rules.py
│   ├── test_routes.py
│   ├── test_no_leakage.py
│   └── test_answer_schema.py
└── docs/
    ├── demo_script.md
    └── blog_draft.md
```

---

## 7. Prerequisites and setup

**Prerequisites**

- Python 3.11+
- TigerGraph **Savanna** (https://savanna.tgcloud.io) or **Community Edition** (https://dl.tigergraph.com), both free
- TigerGraph MCP (https://github.com/tigergraph/tigergraph-mcp)
- An LLM API key and an embedding model (any provider; use JSON/structured output)
- About 16 GB RAM if running Community Edition locally, since `transactions.csv` is about 708 MB

**Install**

```bash
git clone <your-repo-url> && cd <repo>
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
mkdir -p data/raw    # place the 4 CSVs here
```

**`.env`**

```ini
TG_HOST=https://<your-instance>
TG_GRAPH=FraudGraph
TG_USERNAME=...
TG_PASSWORD=...

LLM_PROVIDER=...
LLM_MODEL=...
LLM_API_KEY=...
EMBEDDING_MODEL=...

MAX_EVIDENCE_ROUNDS=2
```

Policy thresholds (0.30 case, 0.70 R1, 0.85/0.15 stop, $500, $1,000, $2,500) live as named constants in `agent/policy/`, not in `.env`. They come from the policy and must not be tuned.

**Savanna:** create a workspace, **enable auto-stop and auto-start** (required), and warm the instance with a trivial query before demos and benchmark runs. Stop the workspace when not in use.

**Community Edition:** install, `gadmin start all`, and confirm GraphStudio and the REST endpoint respond.

**MCP:** follow https://github.com/tigergraph/tigergraph-mcp and point it at the same instance. Then:

```bash
make check-mcp    # lists MCP tools; installed GSQL queries must appear
```

---

## 8. Loading the data

```bash
make schema            # vertex/edge types, vector attributes
make derive-cards      # derive card_id per transaction; must reproduce every known card ID
make load              # loading jobs for all four CSVs
make install-queries   # install GSQL queries
make ingest-docs       # policy, pattern text, regulatory docs → vector store
make ingest-closed     # embed closed-case notes
make verify-load       # row-count and ID checks below
```

`make verify-load` must confirm:

| Check | Expected |
|---|---|
| Transactions | 590,742 |
| Identity records linked | 144,432 (online transactions only) |
| Closed cases | 5,565 (4,665 confirmed, 900 cleared) |
| Case pack | 20, and each `flagged_txn_id`, `card_id`, `customer_id` exists in the graph |
| Columns | 397 transaction columns (393 original + `customer_id, ts, channel, risk_score`) and 41 identity columns, all retrievable |
| `ts` | equals 2016-07-02 00:00:00 + `TransactionDT` seconds for every row |
| Derived `card_id` | reproduces the card for **every** transaction listed in `closed_cases_history.csv` (`txn_ids` → `card_id`) and every `flagged_txn_id` in `case_pack.csv` |
| `W` transactions | have no identity record and `channel = in_person` |

**Deriving `card_id`** (`scripts/derive_card_ids.py`). `transactions.csv` has no card column, so:

1. For each `customer_id`, list the distinct `card2, card3, card4, card5, card6` combinations (and check whether `card1` is one-to-one with `customer_id`).
2. Build ground truth: join `closed_cases_history.csv` (`txn_ids` split on `|`, with `card_id`) and `case_pack.csv` (`flagged_txn_id`, `card_id`) to `transactions.csv`.
3. Find the rule that maps each customer's card combination to `K1`, `K2`, ... and reproduces **100%** of the ground-truth pairs (candidates: order of first appearance, order by frequency, sorted key). Do not accept a rule with any mismatch.
4. Apply the rule to all 590,742 transactions. Persist `TransactionID → card_id` and assert every customer and card in the closed cases and case pack exists afterward.
5. If no simple rule reproduces the ground truth, ask the mentors on Discord before continuing, because every card-level query depends on it.

Loading tips: load in batches, index the hot path (card → transactions ordered by time → device/region/email), and parse `connected_card_ids` and `txn_ids` by splitting on `|`.

**Regulatory documents** (README section "Regulatory references"): load the ones you find useful into the vector store. The most useful for this task are the FinCEN SAR narrative guidance (the standard `sar.narrative` is written to), the FinCEN account-takeover advisory, and the FFIEC red flags and SAR sections. Keep a `docs/sources.md` listing what was ingested.

---

## 9. Agent workflow and tools

### 9.1 Triggers (`agent/triggers.py`)

| Trigger | Case-pack count | Handling |
|---|---|---|
| `risk_score` | 11 | Score is a reason to look, **not** a verdict. Single signal, so R1 applies unless probability is at or above 0.70 |
| `customer_report` | 8 | "I never made this" is a signal, not proof. The customer may be disputing a legitimate recurring charge (R7). Check the recurring pattern before treating it as an R2 denial |
| `analyst_request` | 1 | Open-ended. Look at other cards on the same device or region, not only the flagged card (rings, R6, R9) |

The flagged transaction is where the alert fired. It is **not necessarily where the fraud started, and may not be fraud at all.** The agent must find `first_suspicious_txn_id` and the full episode.

### 9.2 Evidence tools (GSQL through MCP)

| Tool | Purpose |
|---|---|
| `card_window(card_id, hours)` | Velocity, amounts, ProductCD, channel and device in a window around the flagged transaction (card testing, structuring, bursts) |
| `card_baseline(card_id)` | Normal regions, devices, amounts, products, hours; days since first activity |
| `device_neighbors(device_profile, window)` | Other cards or customers using the same device profile; `New` on this account? proxy? |
| `region_cluster(billing_region, window)` | Other cards with new activity in the same region |
| `email_neighbors(email_domain, window)` | Shared purchaser/recipient email |
| `recurring_pattern(card_id, txn_id)` | Same amount and product monthly (R7). "Merchant" is not a column, so use amount + ProductCD + email domains as proxies and say so. Match amounts with a small tolerance because `TransactionAmt` was disguised with small offsets |
| `communities()` | WCC/Louvain on the card-device(-region) graph to surface rings |
| `similar_closed_cases(...)` | Jaccard/cosine on shared entities plus vector similarity on notes |
| `pattern_*` (five) | One detector per documented pattern |
| `discovery_*` | Detectors for undocumented behavior (device rings, sub-threshold structuring) |
| `write_case(...)` | Persist the case, evidence and actions to the graph |

Unnamed features (`V`, `C`, `D`, `M`, numeric `id_*`) may be used as signals. Evidence must call them "unnamed model features".

### 9.3 GraphRAG

Retrieval returns a **structured brief**, not raw rows: case subgraph summary (entities, shared devices/regions, anomalies vs baseline); linked policy rules and pattern descriptions relevant to the candidate patterns; similar closed cases with outcome, pattern and analyst notes; relevant regulatory guidance (especially for the SAR narrative). The LLM receives the brief and returns schema-validated JSON.

### 9.4 Assessment

- Output `fraud_probability` (0-1), candidate `pattern`, and the list of **independent** evidence items. Calibration is scored, so be honest, and the probability may be far from the risk score.
- `verdict`: `fraud`, `legitimate` or `uncertain`. `uncertain` is valid and earns full credit on designed-ambiguous cases **if actions follow R1 and R8**.
- Compute `exposure_usd` as the sum of **absolute** amounts of `affected_txn_ids`, including the flagged one (Policy section 4).

### 9.5 Explanation

Every recommendation states the evidence used, why more evidence was requested (if it was), and why the actions follow from policy, **citing rule numbers**. Each `evidence[]` item has `claim`, `source` (`graph` | `document` | `customer` | `external`), `ref` (query name, document section or request id) and `entity_ids`.

---

## 10. Policy engine (Fraud Policy v1.0)

Implemented as deterministic code in `agent/policy/`. Identifiers below are exact.

### 10.1 Actions and approval routes

| Action | Route |
|---|---|
| `ALLOW_TRANSACTION`, `MONITOR_CARD`, `MONITOR_CONNECTED_CARDS`, `WARN_CUSTOMER`, `VERIFY_WITH_CUSTOMER`, `STEP_UP_AUTH`, `GENERATE_REPORT`, `CREATE_CASE`, `ESCALATE_TO_ANALYST`, `CLOSE_NO_FRAUD` | `auto` |
| `DECLINE_TRANSACTION` | `L1` (team lead) |
| `BLOCK_CARD` | `L1` if exposure ≤ $2,500, `L2` if exposure > $2,500 |
| `BLOCK_ALL_CARDS` | `L2` always |
| `FILE_REPORT` | `L2` always |

The agent recommends. **Only `auto` actions may be executed by the agent.** `L1`/`L2` actions are recommended with the route stated and wait for a human. Order actions by what happens first.

### 10.2 Rules

| Rule | Condition | Recommend |
|---|---|---|
| **R1** | Case rests on a single signal (including risk score alone) and probability < 0.70 | `VERIFY_WITH_CUSTOMER` or `STEP_UP_AUTH` **before any block** |
| **R2** | Customer denies | `BLOCK_CARD` + `CREATE_CASE`; add `FILE_REPORT` if exposure > $1,000 or the case connects to a shared device profile or another card's fraud |
| **R3** | Customer confirms | `CLOSE_NO_FRAUD`; note the confirmation in the case |
| **R4** | No reply within 24 h | `MONITOR_CARD` + `DECLINE_TRANSACTION` for pending authorizations; escalate if exposure > $500 |
| **R5** | Card testing: 3+ small online authorizations on one card within an hour, then a larger purchase | `DECLINE_TRANSACTION` + `STEP_UP_AUTH`; if a purchase over $100 already cleared, `BLOCK_CARD` |
| **R6** | Several cards show fraud from the same device profile, billing region or recipient email in one window | Name the shared element; `CREATE_CASE`, `FILE_REPORT`, and `MONITOR_CONNECTED_CARDS` for every card sharing it |
| **R7** | Customer disputes a charge matching their own recurring pattern (same merchant, amount, monthly) | `CREATE_CASE`, `VERIFY_WITH_CUSTOMER`, `WARN_CUSTOMER`. **Do not block** |
| **R8** | Verdict `uncertain` and exposure > $500, or evidence conflicts | `ESCALATE_TO_ANALYST` |
| **R9** | Fits no known pattern but shows coordinated/repeated abuse across customers | `CREATE_CASE`, `FILE_REPORT`, `ESCALATE_TO_ANALYST`; describe the pattern in your own words; do not force a known category |
| **R10** | Never `BLOCK_ALL_CARDS` unless at least two of the customer's cards show confirmed fraud or credentials are confirmed compromised | (guardrail) |

### 10.3 A case is not a report (Policy 3a)

- **`CREATE_CASE`** when: fraud probability reaches **0.30**, **or** evidence is requested, **or** a customer disputes a charge. Written to the graph.
- **`FILE_REPORT` (SAR)** only when fraud is confirmed or strongly suspected **and** at least one holds: exposure > $1,000; connects to a shared device profile, shared region cluster or another customer's fraud; coordinated or undocumented (R9). A report always has a case behind it. Most cases never need a report.

Deciding "case only" vs "case plus report" is part of the next-best-action score.

### 10.4 Two-stage recommendation (Policy 3b)

Recommend what the evidence supports now (`initial`), request evidence if the policy calls for it, then recommend again (`final`). Example: probability 0.45 on a single signal, so `VERIFY_WITH_CUSTOMER` under R1. Customer denies, so `BLOCK_CARD`, `CREATE_CASE`, possibly `FILE_REPORT` (R2), with connected cards monitored.

### 10.5 Stopping rules

Stop when **one** holds (Policy section 6):

1. Probability is **≥ 0.85 or ≤ 0.15**, supported by **at least two independent pieces of evidence**.
2. A verification response settles the question.
3. Further steps are unlikely to change the decision. State this in `stop_reason`.

Stopping too late wastes effort and stopping too early creates risk. Both are marked down.

### 10.6 Enforcement

- The LLM proposes verdict, probability, pattern and evidence. **`rules.py` maps them to the permitted action set and routes.** The LLM's proposed actions are validated and corrected, never trusted.
- `router.py` derives routes from actions and exposure. An unapproved `L1`/`L2` action can never be executed.
- Every proposed, executed and pending action is logged on the case and in the graph.

`tests/test_policy_rules.py` is the executable spec for this section: build `agent/policy/actions.py` (the `Action`/`Route` enums), `agent/policy/engine.py` (`CaseContext`, `evaluate()`) and `agent/policy/router.py` (`route_for_action()`) to make it pass before wiring the policy engine into the agent loop. A few tests reference `CaseContext` fields (`evidence_conflicts`, `large_purchase_cleared`) that aren't in the minimal field list above — add them to your real `CaseContext` as you implement the corresponding rule, or adjust the test if you model the condition differently; the field names are illustrative, the *behavior* each test asserts is not.

---

## 11. Case memory and leakage rules

**Memory:** the 5,565 closed cases (embedded notes plus graph links to transactions, cards, connected cards) and the agent's own earlier cases.

**Retrieval:** graph similarity (shared device profile, region, email, pattern) combined with vector similarity over notes.

**Rules:**

1. **Temporal filter, per case.** For any investigation, retrieve only closed cases with `closed_at < this case's opened_at`. All 5,565 closed cases end by 2016-11-06, before the first benchmark case (2016-11-12), but the filter is still enforced, and it is essential in backtests.
2. Run the 20 benchmark cases **in chronological order of `opened_at`**. A benchmark case may retrieve agent-written cases that opened **earlier** (for example, a ring found in HHG-014 helps a later case), never later ones.
3. Agent-written cases are **not ground truth**. Store them with `source='agent'` and no confirmed outcome.
4. `similar_prior_cases` in the answer contains **only `CC-####` IDs** from `closed_cases_history.csv` that were actually retrieved and used.
5. Never use the public IEEE-CIS/Kaggle files or any external source of outcomes.
6. `tests/test_no_leakage.py` fails the build if any retrieval returns a case dated on or after the case being investigated.

---

## 12. Simulated evidence requests

Replies are not provided. The agent may request, **without approval**: `customer_validation`, `step_up_auth`, `analyst_info`.

- Each request is an action that passes through the policy engine and is logged.
- Simulators in `agent/simulators/` return a response that is **chosen from the evidence, then recorded** as `assumed_response` in `evidence_requests` (with `asked_after_step`). The `final` actions reflect that assumption.
- **Do not peek at hidden truth.** The simulator must not use anything the agent could not know. Use a transparent rule, for example: assume the customer denies if the assessed probability is at or above 0.5 and the evidence is coherent, otherwise assume confirmation. State the rule in the case.
- Support all policy branches in the simulator: deny (R2), confirm (R3), no reply within 24 h (R4). The UI can show the counterfactual branches. The answer file records the single assumed branch.
- Requesting evidence opens a case (Policy 3a).

---

## 13. Answer files and validator

One file per case at `cases/<case_id>.json`. Fields (exact names):

```jsonc
{
  "case_id": "HHG-001",
  "case": {
    "status": "open | closed_fraud | closed_legitimate | escalated",
    "verdict": "fraud | legitimate | uncertain",
    "fraud_probability": 0.0,
    "pattern": "card_testing | card_not_present_fraud | card_not_present_new_device | out_of_region_use | account_takeover | undocumented | none",
    "pattern_description": "",        // required (2-3 sentences) if pattern == undocumented, else ""
    "affected_txn_ids": [],           // includes flagged txn; empty if legitimate
    "first_suspicious_txn_id": "",
    "connected_card_ids": [],
    "connected_device_profiles": [],   // "DeviceInfo | OS | browser | screen"
    "exposure_usd": 0.0,              // sum of absolute amounts of affected_txn_ids
    "evidence": [ { "claim": "", "source": "graph|document|customer|external", "ref": "", "entity_ids": [] } ],
    "similar_prior_cases": [],        // CC-#### IDs only
    "summary": "",                    // 2-6 sentences
    "written_to_graph": true,
    "graph_case_id": ""
  },
  "evidence_requests": [ { "type": "customer_validation|step_up_auth|analyst_info", "asked_after_step": 0, "assumed_response": "" } ],
  "next_best_actions": {
    "initial": [ { "action": "", "route": "auto|L1|L2", "reason": "cite rule, e.g. R1" } ],
    "final":   [ { "action": "", "route": "", "reason": "" } ],
    "what_changed": "nothing or 1-2 sentences"
  },
  "sar": {
    "file": false,
    "reason": "",
    "narrative": "",                  // required if file; 6-12 sentences; who/what/when/where/how/why
    "subjects": [],                   // customer, card, merchant, device IDs named in the narrative
    "total_amount_usd": 0,
    "activity_dates": []              // [first, last] as YYYY-MM-DD
  },
  "stop_reason": "",
  "tool_calls": 0,
  "tokens": 0,
  "latency_s": 0.0
}
```

### Validator (`make validate-answers`)

Fails the build on any of the following:

| Check | Source |
|---|---|
| Exactly 20 files named `<case_id>.json` for every case in `case_pack.csv`, inside `cases/` | Answer Format |
| All enums valid (`status`, `verdict`, `pattern`, `route`, evidence `source`, request `type`, action names) | Answer Format, Policy |
| Every ID (transaction, card, customer, closed case) exists in the graph | Rules |
| `exposure_usd` equals the sum of absolute `TransactionAmt` of `affected_txn_ids`, recomputed from the graph | Policy 4 |
| Legitimate verdict: `affected_txn_ids = []`, `exposure_usd = 0`, `sar.file = false` | Notes |
| `sar.file` is true if and only if `FILE_REPORT` appears in `final`; otherwise `narrative = ""`, `subjects = []`, `total_amount_usd = 0`, `activity_dates = []` | Part 2 |
| SAR narrative is 6-12 sentences and every subject appears in it | Part 2 |
| `pattern_description` is non-empty if and only if `pattern == undocumented` | Part 1 |
| Every route matches the policy table (including `BLOCK_CARD` L1/L2 by exposure) | Policy 2 |
| `BLOCK_ALL_CARDS` only when R10's condition holds | R10 |
| If `evidence_requests` is empty, `final == initial` and `what_changed == "nothing"` | Part 3 |
| Every `reason` cites a rule number | Policy 7 |
| R1 respected: single signal with probability < 0.70 has a verification action before any block | R1 |
| `CREATE_CASE` present when probability ≥ 0.30, evidence was requested or a customer disputed | Policy 3a |
| `FILE_REPORT` criteria met (3a) whenever it appears, and not omitted when they are met | Policy 3a |
| `similar_prior_cases` contain only `CC-` IDs dated before the case | Leakage |
| `written_to_graph = true` implies the `graph_case_id` vertex exists | Part 1 |

The dataset README says the answer key is hidden. The validator checks format and policy consistency, not correctness.

---

## 14. Evaluation and backtesting

Backtest on closed cases (Jul-Oct) with a **held-out slice that is never used to tune anything**, with memory restricted per [section 11](#11-case-memory-and-leakage-rules).

| Metric | Why |
|---|---|
| Pattern accuracy per pattern | Investigation accuracy (25%) |
| Verdict accuracy and **calibration** (Brier score, reliability curve) | `fraud_probability` is scored for calibration |
| Affected-transaction precision/recall and exposure error | Exposure and episode extent |
| Connected-card / device recall (especially the undocumented ring) | Ring detection |
| Action-set and route accuracy against closed-case `actions_taken` | Next best action (25%) |
| Correct "case only" vs "case plus report" | Policy 3a |
| Clearing rate on legitimate alerts (`cleared` cases) | Over-blocking guard |
| Unnecessary evidence requests, and premature stops | Stopping rules |
| Policy violations | Must be **0** |
| `tool_calls`, `tokens`, `latency_s` | Required output fields; efficiency |

Caveats:

- **Class balance.** Closed history is about 84% fraud; the benchmark is about half legitimate. Evaluate on a re-weighted or balanced sample so the agent does not learn "everything is fraud".
- **Labels exist only for closed-case transactions.** Unlabeled transactions are not known to be legitimate.
- The five documented patterns are not the only ones. Include an "undocumented pattern" discovery check in the backtest (the nine `undocumented` closed cases are the seed).

Then freeze the agent and run `make benchmark` once.

**Probability calibration (`eval/calibrate.py`).** Because `fraud_probability` is graded on calibration, not just the verdict, fit a correction rather than trusting the LLM's raw self-reported probability:

```bash
make backtest-predictions   # runs the (uncalibrated) agent over closed cases, dumps raw_fraud_probability
python -m eval.calibrate --predictions data/backtest_predictions.csv --output models/probability_calibrator.pkl
```

The script splits closed cases by `opened_at` (fit: Jul-Sep, held-out: Oct — never fit on the held-out slice), rebalances both slices to the benchmark's ~50% prevalence instead of the closed-case history's ~84% (the base-rate trap noted above), fits an isotonic regression on the fit slice, and reports the Brier score and a reliability table before and after on the untouched held-out slice. `agent/assess.py` loads `models/probability_calibrator.pkl` and applies it to the LLM's raw score before it is written into `case.fraud_probability` in any answer file. If the held-out Brier score doesn't improve, the report says so — don't apply a calibrator that makes things worse.

**Speed.** Two changes carry most of the latency win for a project this size:

- `agent/tools/cache.py` memoizes read-only graph queries keyed on `(args, as_of)` — safe within a run since the graph only grows, and doubles as an enforcement point for the leakage rule (`as_of` is a required argument). Check `cache_stats()` after a benchmark run; a low hit rate usually means `as_of` is being passed inconsistently.
- `fetch_case_evidence_parallel` (same file) issues the independent first-round queries (`card_window`, `card_baseline`, `device_neighbors`, `region_cluster`, `email_neighbors`, `similar_closed_cases`) concurrently instead of sequentially, since none of them depend on each other's output. Chained queries that do depend on a prior result (`recurring_pattern` needs a candidate `txn_id` from `card_window` first) stay sequential. A failed tool degrades to `{"degraded": true}` rather than aborting the case — log it, don't crash on it.
- Route cheap, high-volume steps (pattern pre-screen, response classification) to a small/fast model or Jev; keep your strongest model only for final synthesis, explanation and the SAR narrative, which are graded on quality and run once per case.

---

## 15. User interface

Streamlit app (`ui/app.py`) covering the brief's requirement to show the investigation, case progression, evidence, uncertainty, recommendations and next actions:

- Case queue for the 20 alerts, with trigger type and score
- **Case timeline**: status changes, tool calls, decision log
- **Graph view** of the case subgraph (card, transactions, device profiles, regions, connected cards)
- **Evidence panel** with source and rule citations
- **Probability and stop-rule display**: why it stopped or asked for more
- **Initial vs final actions** side by side with routes, and `what_changed`
- **Approval queue**: `L1`/`L2` items waiting for a human; `auto` items shown as executed
- Similar closed cases with outcome and notes
- SAR preview where required

---

## 16. Optional: autonomous monitoring

Separate folder `autonomous/` (**counts toward Innovation, not accuracy**): the agent scans the exam period on its own, picks up alerts from risk scores, and investigates beyond the 20 cases. Suggested: rank cards by graph signals (shared new device profiles, structuring under $500, out-of-region bursts), run the same policy-bound investigation loop, and write outputs in the same answer format. Do not mix these files into `cases/`.

Benchmark answer files in `cases/` are the grading source of truth. Runtime API artifacts in `output/` are derived operational data and must not be used as a second benchmark submission.

---

## 17. Build order

**First two hours (from the dataset README):**

1. Read the dataset README once, top to bottom, including the Answer Format.
2. Get TigerGraph running (Savanna with auto-stop/auto-start, or Community Edition).
3. Derive `card_id` (there is no such column, see section 8), then load Customer, Card, Transaction and their edges. Then add DeviceProfile, EmailDomain, BillingRegion, ClosedCase.
4. Connect TigerGraph MCP.
5. **Investigate one case by hand** before writing agent code. HHG-017 (risk score 0.57, hidden proxy, device `Found`) and HHG-014 (analyst ring request) are good contrasts.
6. Write the first answer file by hand, then automate.

**Phases:**

| Phase | Work |
|---|---|
| 1. Graph and data | Schema, load, `make verify-load`; explore closed cases |
| 2. Detection | GSQL for the five patterns, ring detection (WCC/Louvain), discovery queries for the undocumented behaviors |
| 3. GraphRAG and memory | Ingest policy, pattern text, regulatory docs, closed-case notes; similar-case retrieval with the temporal filter |
| 4. Policy engine | R1-R10, routes, case/SAR criteria, stopping rules, unit tests first |
| 5. Agent | State machine, tools through MCP, simulators, case write-back, answer-file writer, counters |
| 6. Evaluation | Backtest, calibration, validator, then freeze and run the benchmark once |
| 7. UI, demo, writing | Streamlit, demo video, blog, social post. Start early, since these are required deliverables and 10% of the score |

Demo must include: one case where **low confidence triggers a request and the recommendation changes**; one case correctly **cleared**; one **case-only** (no report) vs one **case plus report**; the **device ring** case; and the approval queue holding an `L1`/`L2` action.

---

## 18. Submission checklist

- [ ] Agent runs end to end from a clean clone using this README
- [ ] `make verify-load` matches the counts in [section 8](#8-loading-the-data)
- [ ] TigerGraph (Savanna or Community) is used for graph **and vector** storage/retrieval
- [ ] Savanna auto-stop and auto-start enabled (if Savanna); warmed before the demo
- [ ] GSQL queries and graph algorithms in use (community detection, similarity)
- [ ] TigerGraph MCP is the agent's graph interface
- [ ] GraphRAG passes structured context (subgraph + policy/typology/regulation + similar cases) to the LLM
- [ ] 20 files in `cases/`, named `<case_id>.json`, passing `make validate-answers`
- [ ] Each case written to the graph, with `graph_case_id`
- [ ] Every answer has `initial` and `final` actions with routes, `what_changed`, and simulated `evidence_requests` where used
- [ ] SARs only where Policy 3a requires them, with standalone narratives
- [ ] Only exact policy action names and routes used; policy-violation count is 0
- [ ] Only `auto` actions executed; `L1`/`L2` left in the approval queue
- [ ] No leakage test passing; benchmark run in chronological order
- [ ] No public IEEE-CIS/Kaggle files used anywhere
- [ ] `tool_calls`, `tokens`, `latency_s` populated for every case
- [ ] 3-5 minute demo video
- [ ] Technical blog post published
- [ ] X or LinkedIn post published with link, **tagging @TigerGraphDB**
- [ ] `.env`, credentials and raw data excluded from the repo
- [ ] Optional: `autonomous/` folder, kept separate from `cases/`

---

## 19. Troubleshooting

| Problem | Fix |
|---|---|
| Savanna queries time out | Workspace auto-stopped. Confirm auto-start is on, send a warm-up query and retry |
| `transactions.csv` load is slow or runs out of memory | Load in batches; keep `V1-V339` compact (list/JSON attribute or sidecar); create indexes after bulk load |
| Derived cards don't match closed cases or the case pack | Do not load yet. Re-run the derivation checks in section 8; the rule for the `-K#` suffix is wrong |
| MCP tools missing | Re-run `make install-queries`, restart the MCP server, `make check-mcp` |
| LLM returns malformed JSON | Schema-constrained output, retry with the validation error, fall back to `ESCALATE_TO_ANALYST` |
| Agent blocks too much | Check R1: single signal below 0.70 needs verification first. Check the clearing rate in the backtest |
| Agent loops on evidence requests | Check `MAX_EVIDENCE_ROUNDS`; the stop rules and R8 should end it |
| Validator: `exposure_usd` mismatch | Recompute from absolute `TransactionAmt` of `affected_txn_ids` in the graph |
| Leakage test fails | A retrieval is missing the `closed_at < opened_at` filter |

---

## 20. Links

- TigerGraph Savanna: https://savanna.tgcloud.io
- TigerGraph Community Edition: https://dl.tigergraph.com
- TigerGraph MCP: https://github.com/tigergraph/tigergraph-mcp
- TigerGraph Discord (mentors/judges): the dataset README lists https://discord.com/invite/4cc7SNqRf and the brief PDF lists https://discord.gg/7JMkCAy9D3. Try either
- FinCEN SAR narrative guidance: https://www.fincen.gov/system/files/shared/sar_guidance_narrative.pdf
- Other regulatory references: see the dataset README, "Regulatory references"

## License

Add your chosen license here.
