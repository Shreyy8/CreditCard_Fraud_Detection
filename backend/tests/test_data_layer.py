import csv

from app import data_layer
from app.data_layer import DataLayer


def write_csv(path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_card_history_uses_derived_card_mapping(tmp_path, monkeypatch):
    transactions_path = tmp_path / "transactions.csv"
    mapping_path = tmp_path / "transaction_cards.csv"
    write_csv(
        transactions_path,
        ["TransactionID", "customer_id", "ts"],
        [
            {"TransactionID": "T1", "customer_id": "C1", "ts": "2020-01-01"},
            {"TransactionID": "T2", "customer_id": "C1", "ts": "2020-01-02"},
        ],
    )
    write_csv(
        mapping_path,
        ["TransactionID", "customer_id", "card_id", "mapping_source"],
        [
            {"TransactionID": "T1", "customer_id": "C1", "card_id": "C1-K1", "mapping_source": "known_anchor"},
            {"TransactionID": "T2", "customer_id": "C1", "card_id": "C1-K2", "mapping_source": "known_anchor"},
        ],
    )
    monkeypatch.setattr(data_layer.settings, "transactions_csv", str(transactions_path))
    monkeypatch.setattr(data_layer.settings, "transaction_cards_csv", str(mapping_path))

    layer = DataLayer()
    layer._load_transaction_cards()
    layer._load_transactions()

    assert [row["TransactionID"] for row in layer.get_card_transactions("C1-K1")] == ["T1"]
    assert [row["TransactionID"] for row in layer.get_card_transactions("C1-K2")] == ["T2"]
    assert layer.get_card_transactions("C1-K3") == []