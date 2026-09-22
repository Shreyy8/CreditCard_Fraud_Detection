"""Focused grounding and runtime-context tests."""

from app.agents.fraud_agent import validate_grounded_llm_output


def test_unknown_entity_is_rejected_from_llm_evidence():
    context = {
        "trigger": {"txn_id": "txn-1"},
        "graph_evidence": [{"entity_ids": ["txn-1"]}],
        "mcp_evidence": [],
        "historical_cases": [],
        "policy_evidence": [],
    }
    accepted, counters = validate_grounded_llm_output(
        context,
        {"evidence": [{"claim": "Unknown device", "entity_ids": ["device-unknown"]}]},
    )

    assert accepted == []
    assert counters == {"fabricated_entities": 1, "unsupported_claims": 1}


def test_known_entity_is_retained():
    context = {
        "trigger": {"txn_id": "txn-1"},
        "graph_evidence": [{"entity_ids": ["txn-1"]}],
        "mcp_evidence": [],
        "historical_cases": [],
        "policy_evidence": [],
    }
    accepted, counters = validate_grounded_llm_output(
        context,
        {"evidence": [{"claim": "Observed transaction", "entity_ids": ["txn-1"]}]},
    )

    assert len(accepted) == 1
    assert counters == {"fabricated_entities": 0, "unsupported_claims": 0}
