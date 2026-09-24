"""Shared invariants that must hold for every case-pack investigation."""

from __future__ import annotations

import pytest

from app.agents.fraud_agent import FraudAgent
from app.data_layer import get_data_layer
from app.models.case import FraudPattern


DATA = get_data_layer()
CASE_IDS = [row["case_id"] for row in DATA.get_all_case_pack_rows()]


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_exposure_matches_flagged_and_burst_rule(case_id: str) -> None:
    data = get_data_layer()
    agent = FraudAgent()

    row = data.get_case_pack_row(case_id)
    state = agent._init_state(row)
    state.flagged_txn = data.get_transaction(row["flagged_txn_id"]) or {}
    state.customer_history = data.get_customer_transactions(row["customer_id"])
    state.connected_entities["identity"] = data.get_identity(row["flagged_txn_id"])
    state.connected_entities["card_transactions"] = data.get_card_transactions(
        row["card_id"]
    )
    state.pattern = agent._detect_pattern(state).pattern

    exposure = agent._calculate_exposure(state)

    assert row["flagged_txn_id"] in exposure.affected_txn_ids
    expected = sum(
        float(data.get_transaction(txn_id)["TransactionAmt"])
        for txn_id in exposure.affected_txn_ids
    )
    assert exposure.exposure_usd == round(expected, 2)
    if row["trigger_type"] == "customer_report":
        assert exposure.affected_txn_ids == [row["flagged_txn_id"]]
    elif len(exposure.affected_txn_ids) > 1:
        assert state.pattern in {
            FraudPattern.card_not_present_fraud,
            FraudPattern.card_not_present_new_device,
            FraudPattern.card_testing,
        }, f"{case_id} has multi-transaction exposure without a burst pattern"


def test_customer_report_exposure_is_limited_to_disputed_transaction() -> None:
    data = get_data_layer()
    agent = FraudAgent()
    row = data.get_case_pack_row("HHG-006")
    state = agent._init_state(row)
    state.flagged_txn = data.get_transaction(row["flagged_txn_id"])
    state.customer_history = data.get_customer_transactions(row["customer_id"])
    state.connected_entities["card_transactions"] = data.get_card_transactions(
        row["card_id"]
    )
    state.pattern = agent._detect_pattern(state).pattern

    exposure = agent._calculate_exposure(state)

    assert exposure.affected_txn_ids == ["3476682"]
    assert exposure.exposure_usd == 482.12