from pathlib import Path

from graph_loader import build_records


def _write_csv(path: Path, header: str, rows: list[str]) -> None:
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")


class Settings:
    transactions_csv = "transactions.csv"
    identity_csv = "identity.csv"
    transaction_cards_csv = "transaction_cards.csv"
    closed_cases_csv = "closed_cases.csv"
    case_pack_csv = "case_pack.csv"


def test_build_records_creates_domain_entities(tmp_path, monkeypatch):
    _write_csv(
        tmp_path / "transactions.csv",
        "TransactionID,TransactionAmt,TransactionDT,ProductCD,customer_id,channel,ts,risk_score,addr1,addr2,P_emaildomain,R_emaildomain,card1,card2,card3,card4,card5,card6",
        ["1,12.50,10,C1,C00001,online,2016-07-02 00:00:10,0.2,111,87,a.com,,1,2,3,4,5,6"],
    )
    _write_csv(tmp_path / "identity.csv", "TransactionID,DeviceInfo,id_15,id_23,id_30,id_31,id_33", ["1,Phone,New,Anonymous,Android,Chrome,1080"])
    _write_csv(tmp_path / "transaction_cards.csv", "TransactionID,customer_id,card_id,mapping_source", ["1,C00001,C00001-K1,anchor"])
    _write_csv(tmp_path / "closed_cases.csv", "case_id,opened_at,outcome", ["CC-0001,2016-06-01 00:00:00,confirmed_fraud"])
    _write_csv(tmp_path / "case_pack.csv", "case_id,opened_at,trigger_type,flagged_txn_id", ["HHG-001,2016-07-03 00:00:00,risk_score,1"])

    monkeypatch.setattr("graph_loader.ROOT", tmp_path)
    records = build_records(Settings())

    assert {item["id"] for item in records["Customer"]} == {"C00001"}
    assert {item["id"] for item in records["Card"]} == {"C00001-K1"}
    assert {item["id"] for item in records["Transaction"]} == {"1"}
    assert records["DeviceProfile"]
    assert records["FraudCase"]
    assert any(edge["from"] == "1" for edge in records["ON_CARD"])