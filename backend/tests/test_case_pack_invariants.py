"""Shared invariants that must hold for every case-pack investigation."""

from __future__ import annotations

from app.agents.fraud_agent import FraudAgent
from app.data_layer import get_data_layer


def test_all_case_pack_exposures_include_only_selected_transactions() -> None:
    data = get_data_layer()
    agent = FraudAgent()

    for row in data.get_all_case_pack_rows():
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