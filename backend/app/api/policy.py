"""Policy API — exposes Fraud Policy v1.0 rules, routes, and action specifications."""

from fastapi import APIRouter
from ..policy.policy_engine import AUTO_ACTIONS

router = APIRouter(prefix="/policy", tags=["policy"])

POLICY_RULES = [
    {
        "id": "R1",
        "name": "Single-Signal Verification Guard",
        "section": "3.1 Intake Controls",
        "condition": "Case rests on a single signal (including risk score alone) and probability < 0.70",
        "recommendation": "VERIFY_WITH_CUSTOMER or STEP_UP_AUTH before any card block",
        "permissible_routes": ["auto"],
        "category": "intake",
        "rationale": "Prevents customer friction and false block churn on isolated model anomalies.",
        "benchmark_cases_cited": ["HHG-001", "HHG-005", "HHG-008", "HHG-010", "HHG-011", "HHG-013"],
    },
    {
        "id": "R2",
        "name": "Customer Repudiated Charge / Confirmed ATO",
        "section": "3.2 Customer Response Handling",
        "condition": "Customer denies authorizing the transaction(s) via SMS/App validation prompt",
        "recommendation": "BLOCK_CARD + CREATE_CASE. Add FILE_REPORT if exposure > $1,000 or connected to a shared device ring.",
        "permissible_routes": ["L1", "L2"],
        "category": "customer_response",
        "rationale": "Direct cardholder repudiation provides high evidential weight. Immediate account containment is mandated.",
        "benchmark_cases_cited": ["HHG-002", "HHG-003", "HHG-006", "HHG-007", "HHG-008", "HHG-014", "HHG-015", "HHG-017", "HHG-019", "HHG-020"],
    },
    {
        "id": "R3",
        "name": "Customer Confirmed Charge (Legitimate Clearing)",
        "section": "3.2 Customer Response Handling",
        "condition": "Customer explicitly confirms authorization of the transaction(s)",
        "recommendation": "CLOSE_NO_FRAUD. Record confirmation timestamp into graph memory.",
        "permissible_routes": ["auto"],
        "category": "customer_response",
        "rationale": "Ensures legitimate commerce is restored without administrative delay.",
        "benchmark_cases_cited": ["HHG-004", "HHG-010", "HHG-016"],
    },
    {
        "id": "R4",
        "name": "Verification Request SLA Timeout",
        "section": "3.2 Customer Response Handling",
        "condition": "No customer reply within 24 hours of verification dispatch",
        "recommendation": "MONITOR_CARD + DECLINE_TRANSACTION for pending authorizations. ESCALATE_TO_ANALYST if exposure > $500.",
        "permissible_routes": ["auto", "L1"],
        "category": "customer_response",
        "rationale": "Prevents indefinite exposure while avoiding destructive card cancellation if cardholder is traveling or offline.",
        "benchmark_cases_cited": ["HHG-005", "HHG-018"],
    },
    {
        "id": "R5",
        "name": "Card-Testing Velocity Pattern",
        "section": "3.3 Graph & Behavioral Patterns",
        "condition": ">= 3 micro-transactions (< $2.00) within 10-minute sliding window",
        "recommendation": "DECLINE_TRANSACTION + VERIFY_WITH_CUSTOMER; if purchase > $100 already cleared, BLOCK_CARD immediately",
        "permissible_routes": ["L1"],
        "category": "pattern",
        "rationale": "Interprets bot-driven BIN validation before larger cash-out waves can be executed.",
        "benchmark_cases_cited": ["HHG-001", "HHG-015"],
    },
    {
        "id": "R6",
        "name": "Shared Device/IP Multi-Card Ring Discovery",
        "section": "3.3 Graph & Behavioral Patterns",
        "condition": "Device profile is shared across cards belonging to multiple distinct cardholders",
        "recommendation": "MONITOR_CONNECTED_CARDS + CREATE_CASE. If fraud is confirmed on any connected node, expand investigation to full ring.",
        "permissible_routes": ["auto", "L1", "L2"],
        "category": "pattern",
        "rationale": "Leverages TigerGraph multi-hop neighborhood discovery to isolate organized criminal syndicates.",
        "benchmark_cases_cited": ["HHG-002", "HHG-014"],
    },
    {
        "id": "R7",
        "name": "Recurring Charge with Historical Baseline",
        "section": "3.3 Graph & Behavioral Patterns",
        "condition": "Transaction matches merchant, amount (+/- 10%), and billing day of an established recurring cadence active >= 3 months",
        "recommendation": "VERIFY_WITH_CUSTOMER without card block, OR ALLOW_TRANSACTION with WARN_CUSTOMER.",
        "permissible_routes": ["auto"],
        "category": "pattern",
        "rationale": "Prevents interruption of essential subscription services, cloud utilities, or loan payments.",
        "benchmark_cases_cited": ["HHG-004"],
    },
    {
        "id": "R8",
        "name": "Conflicting Evidence or High Uncertainty",
        "section": "3.4 Decision Coordination",
        "condition": "Evidence sources present contradictory signals",
        "recommendation": "ESCALATE_TO_ANALYST. Agent is strictly prohibited from guessing or fabricating consensus.",
        "permissible_routes": ["auto"],
        "category": "coordination",
        "rationale": "Maintains zero false-positive integrity by escalating ambiguous edge-cases to human fraud specialists.",
        "benchmark_cases_cited": ["HHG-005", "HHG-018"],
    },
    {
        "id": "R9",
        "name": "Novel / Undocumented Graph Pattern",
        "section": "3.4 Decision Coordination",
        "condition": "Graph anomaly or behavioral deviation does not fit standard taxonomy",
        "recommendation": "Describe anomaly explicitly in narrative; do NOT force-fit to existing labels. Route action according to exposure ($2,500 threshold).",
        "permissible_routes": ["L1", "L2"],
        "category": "coordination",
        "rationale": "Supports zero-day typology discovery while maintaining rigorous evidentiary documentation.",
        "benchmark_cases_cited": ["HHG-009"],
    },
    {
        "id": "R10",
        "name": "Customer-Level Mass Card-Block Guardrail",
        "section": "3.5 Catastrophic Risk Guardrails",
        "condition": "Action BLOCK_ALL_CARDS is proposed for a customer entity",
        "recommendation": "Permitted ONLY if at least 2 cards belonging to the customer show confirmed fraud OR credentials confirmed breached. Requires L2 approval.",
        "permissible_routes": ["L2"],
        "category": "guardrail",
        "rationale": "Protects the cardholder relationship from total account severance on an isolated compromised card.",
        "benchmark_cases_cited": ["HHG-012"],
    },
]

ROUTE_SPECIFICATIONS = [
    {"action": "ALLOW_TRANSACTION", "route": "auto", "authority": "Agent Direct Execution"},
    {"action": "MONITOR_CARD", "route": "auto", "authority": "Agent Direct Execution"},
    {"action": "MONITOR_CONNECTED_CARDS", "route": "auto", "authority": "Agent Direct Execution"},
    {"action": "WARN_CUSTOMER", "route": "auto", "authority": "Agent Direct Execution"},
    {"action": "VERIFY_WITH_CUSTOMER", "route": "auto", "authority": "Agent Direct Execution"},
    {"action": "STEP_UP_AUTH", "route": "auto", "authority": "Agent Direct Execution"},
    {"action": "GENERATE_REPORT", "route": "auto", "authority": "Agent Direct Execution"},
    {"action": "CREATE_CASE", "route": "auto", "authority": "Agent Direct Execution"},
    {"action": "ESCALATE_TO_ANALYST", "route": "auto", "authority": "Agent Direct Execution"},
    {"action": "CLOSE_NO_FRAUD", "route": "auto", "authority": "Agent Direct Execution"},
    {"action": "DECLINE_TRANSACTION", "route": "L1", "authority": "Senior Investigator / Team Lead Approval"},
    {"action": "BLOCK_CARD", "route": "L1 / L2", "authority": "L1 if exposure <= $2,500; L2 if exposure > $2,500"},
    {"action": "BLOCK_ALL_CARDS", "route": "L2", "authority": "Fraud Operations Manager (R10 mandatory double-card check)"},
    {"action": "FILE_REPORT", "route": "L2", "authority": "BSA / AML Compliance Officer Sign-off"},
]


@router.get("/rules")
async def get_policy_rules():
    """Return all Fraud Policy v1.0 rules."""
    return {"rules": POLICY_RULES}


@router.get("/actions")
async def get_policy_actions():
    """Return all action route specifications and tier definitions."""
    return {
        "routes": ROUTE_SPECIFICATIONS,
        "auto_actions": [a.value for a in AUTO_ACTIONS],
    }
