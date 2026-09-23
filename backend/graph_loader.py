"""Repeatable CSV-to-TigerGraph loader for FraudCaseGraph.

The loader is intentionally explicit: it uses the derived transaction card
artifact and never downloads or infers outcomes from public IEEE-CIS data.
Run with ``--dry-run`` first, then ``--reset`` only when a full reload is
intended.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from app.config import get_settings
from app.tigergraph.client import TigerGraphClient


ROOT = Path(__file__).resolve().parent.parent


def _path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _text(value: Any) -> str:
    return str(value or "").strip()


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _datetime(value: Any) -> str:
    value = _text(value)
    if not value:
        return ""
    return value.replace("+00:00", "")


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_records(settings) -> dict[str, list[dict[str, Any]]]:
    """Build bounded vertex/edge records from the supplied local dataset."""
    txns = _read(_path(settings.transactions_csv))
    identities = {r["TransactionID"]: r for r in _read(_path(settings.identity_csv))}
    cards = {
        r["TransactionID"]: r
        for r in _read(_path(settings.transaction_cards_csv))
        if _text(r.get("card_id"))
    }
    closed = _read(_path(settings.closed_cases_csv))
    benchmark = _read(_path(settings.case_pack_csv))

    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)

    def add(kind: str, record: dict[str, Any]) -> None:
        key = _text(record.get("id"))
        if key and key not in seen[kind]:
            out[kind].append(record)
            seen[kind].add(key)

    customer_cards: dict[str, set[str]] = defaultdict(set)
    for row in txns:
        tid = _text(row.get("TransactionID"))
        customer = _text(row.get("customer_id"))
        mapping = cards.get(tid, {})
        card = _text(mapping.get("card_id"))
        if customer:
            add("Customer", {"id": customer, "customer_id": customer})
        if card:
            customer_cards[customer].add(card)
            add("Card", {
                "id": card, "card_id": card, "customer_id": customer,
                **{f"card{i}": _text(row.get(f"card{i}")) for i in range(1, 7)},
            })
        add("Transaction", {
            "id": tid, "transaction_id": tid,
            "transaction_amt": _float(row.get("TransactionAmt")),
            "transaction_dt": int(_float(row.get("TransactionDT"))),
            "product_cd": _text(row.get("ProductCD")), "customer_id": customer,
            "card_id": card, "channel": _text(row.get("channel")),
            "ts": _datetime(row.get("ts")), "risk_score": _float(row.get("risk_score")),
            "addr1": _text(row.get("addr1")), "addr2": _text(row.get("addr2")),
            "p_emaildomain": _text(row.get("P_emaildomain")),
            "r_emaildomain": _text(row.get("R_emaildomain")),
        })
        if customer and card:
            out["OWNS"].append({"from": customer, "to": card})
        if customer:
            out["MADE"].append({"from": customer, "to": tid, "ts": _datetime(row.get("ts"))})
        if card:
            out["ON_CARD"].append({"from": tid, "to": card, "ts": _datetime(row.get("ts"))})
            out["transaction_belongs_to_card"].append({"from": tid, "to": card})
        if customer:
            out["transaction_belongs_to_customer"].append({"from": tid, "to": customer})

        identity = identities.get(tid)
        if identity:
            device_key = " | ".join(
                _text(identity.get(column))
                for column in ("DeviceInfo", "id_30", "id_31", "id_33")
                if _text(identity.get(column))
            )
            if device_key:
                add("DeviceProfile", {
                    "id": device_key, "device_key": device_key,
                    "device_info": _text(identity.get("DeviceInfo")),
                    "operating_system": _text(identity.get("id_30")),
                    "browser": _text(identity.get("id_31")),
                    "screen": _text(identity.get("id_33")),
                    "proxy_type": _text(identity.get("id_23")),
                })
                add("Identity", {
                    "id": tid, "identity_id": tid, "transaction_id": tid,
                    "device_info": _text(identity.get("DeviceInfo")),
                    "id_15": _text(identity.get("id_15")), "id_23": _text(identity.get("id_23")),
                    "id_30": _text(identity.get("id_30")), "id_31": _text(identity.get("id_31")),
                    "id_33": _text(identity.get("id_33")), "device_key": device_key,
                })
                out["FROM_DEVICE"].append({"from": tid, "to": device_key, "ts": _datetime(row.get("ts")), "is_new": _text(identity.get("id_15")) == "New"})
                out["transaction_has_identity"].append({"from": tid, "to": tid})
            for column in ("P_emaildomain", "R_emaildomain"):
                email = _text(row.get(column))
                if email:
                    add("EmailDomain", {"id": email, "email_domain": email})
                    out["PURCHASER_EMAIL"].append({"from": tid, "to": email, "email_type": column})
        region = _text(row.get("addr1"))
        if region:
            add("BillingRegion", {"id": region, "region_id": region, "country_code": _text(row.get("addr2"))})
            out["BILLED_IN"].append({"from": tid, "to": region, "addr2": _text(row.get("addr2"))})

    for row in closed + benchmark:
        cid = _text(row.get("case_id"))
        if not cid:
            continue
        add("FraudCase", {
            "id": cid, "case_id": cid, "opened_at": _datetime(row.get("opened_at")),
            "closed_at": _datetime(row.get("closed_at")), "trigger_type": _text(row.get("trigger_type")),
            "trigger_text": _text(row.get("trigger_text")), "outcome": _text(row.get("outcome")),
            "verdict": _text(row.get("outcome")), "pattern": _text(row.get("pattern")),
            "risk_score": _float(row.get("risk_score")), "exposure_usd": _float(row.get("exposure_usd")),
            "txn_ids": _text(row.get("txn_ids") or row.get("flagged_txn_id")), "n_txns": 1,
            "connected_card_ids": _text(row.get("connected_card_ids")),
            "actions_taken": _text(row.get("closed_actions")), "report_filed": _text(row.get("sar_filed")) == "true",
            "analyst_notes": _text(row.get("notes")),
        })

    for customer, cards_for_customer in customer_cards.items():
        for card in cards_for_customer:
            out["OWNS"].append({"from": customer, "to": card})
    return dict(out)


def load_records(records: dict[str, list[dict[str, Any]]]) -> tuple[int, int]:
    """Upsert records using the direct TigerGraph client.

    Returns ``(vertices, edges)``. Duplicate edges are collapsed by endpoint
    and type before upload because the source files contain repeated customer
    and card observations.
    """
    client = TigerGraphClient()
    vertex_types = {
        "Customer", "Card", "Transaction", "Identity", "DeviceProfile",
        "EmailDomain", "BillingRegion", "FraudCase", "Evidence", "Document",
    }
    vertices = 0
    edges = 0
    for kind, items in records.items():
        if kind in vertex_types:
            for item in items:
                attrs = {key: value for key, value in item.items() if key != "id"}
                if client.upsert_vertex(kind, str(item["id"]), attrs):
                    vertices += 1

    edge_types = {
        "OWNS": ("Customer", "Card"), "MADE": ("Customer", "Transaction"),
        "FROM_DEVICE": ("Transaction", "DeviceProfile"),
        "PURCHASER_EMAIL": ("Transaction", "EmailDomain"),
        "BILLED_IN": ("Transaction", "BillingRegion"),
        "ON_CARD": ("Transaction", "Card"),
        "transaction_belongs_to_card": ("Transaction", "Card"),
        "transaction_belongs_to_customer": ("Transaction", "Customer"),
        "transaction_has_identity": ("Transaction", "Identity"),
    }
    seen_edges: set[tuple[str, str, str]] = set()
    for kind, endpoints in edge_types.items():
        for item in records.get(kind, []):
            key = (kind, str(item.get("from", "")), str(item.get("to", "")))
            if not key[1] or not key[2] or key in seen_edges:
                continue
            seen_edges.add(key)
            attrs = {k: v for k, v in item.items() if k not in {"from", "to"}}
            if client.upsert_edge(endpoints[0], key[1], kind, endpoints[1], key[2], attrs):
                edges += 1
    client.close()
    return vertices, edges


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--load", action="store_true", help="upsert records into Savanna")
    args = parser.parse_args()
    settings = get_settings()
    records = build_records(settings)
    counts = {key: len(value) for key, value in records.items()}
    print(counts)
    if args.dry_run:
        return 0
    if not args.load:
        raise SystemExit("Pass --dry-run or --load explicitly")
    vertices, edges = load_records(records)
    print(f"uploaded vertices={vertices} edges={edges}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())