"""Deterministic pattern detection over local case-profile artifacts.

The detectors return evidence candidates only. They do not assign a final
verdict, probability, or policy action.
"""

from __future__ import annotations

from datetime import datetime
from itertools import combinations
from typing import Any


SMALL_AUTHORIZATION_USD = 5.0
LARGE_PURCHASE_USD = 100.0
CARD_TEST_WINDOW_SECONDS = 60 * 60
STRUCTURING_WINDOW_SECONDS = 40 * 60
STRUCTURING_LIMIT_USD = 500.0


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def _amount(transaction: dict[str, Any]) -> float:
    return float(transaction.get("TransactionAmt") or 0.0)


def _evidence(pattern: str, claim: str, transaction_ids: list[str], **details: Any) -> dict[str, Any]:
    return {
        "pattern": pattern,
        "matched": True,
        "confidence": details.pop("confidence", 0.0),
        "transaction_ids": sorted(set(transaction_ids)),
        "connected_card_ids": details.pop("connected_card_ids", []),
        "evidence": [{"claim": claim, **details}],
        "counter_evidence": [],
    }


def _no_match(pattern: str, reason: str) -> dict[str, Any]:
    return {
        "pattern": pattern,
        "matched": False,
        "confidence": 0.0,
        "transaction_ids": [],
        "connected_card_ids": [],
        "evidence": [],
        "counter_evidence": [reason],
    }


def detect_card_testing(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    online = sorted(
        (transaction for transaction in transactions if transaction.get("channel") == "online"),
        key=lambda transaction: _timestamp(transaction["ts"]),
    )
    for start_index in range(len(online)):
        start_time = _timestamp(online[start_index]["ts"])
        small = []
        for candidate in online[start_index:]:
            elapsed = (_timestamp(candidate["ts"]) - start_time).total_seconds()
            if elapsed > CARD_TEST_WINDOW_SECONDS:
                break
            if _amount(candidate) < SMALL_AUTHORIZATION_USD:
                small.append(candidate)
            elif _amount(candidate) > LARGE_PURCHASE_USD and len(small) >= 3:
                ids = [item["TransactionID"] for item in small] + [candidate["TransactionID"]]
                return _evidence(
                    "card_testing",
                    "At least three small online authorizations were followed by a larger purchase within one hour.",
                    ids,
                    confidence=0.95,
                    small_authorization_count=len(small),
                    larger_purchase_id=candidate["TransactionID"],
                    window_seconds=round(elapsed),
                )
    return _no_match("card_testing", "No qualifying sequence of three small authorizations and a larger purchase was found.")


def detect_shared_entity(case_id: str, shared_entities: dict[str, Any]) -> dict[str, Any]:
    shared = shared_entities.get(case_id, {})
    connected_customers = shared.get("connected_customer_ids", [])
    connected_cards = shared.get("connected_card_ids", [])
    devices = shared.get("shared_devices", {})
    qualifying_devices = {
        device: matches for device, matches in devices.items()
        if len({match.get("customer_id") for match in matches}) >= 2
    }
    if not qualifying_devices:
        return _no_match("shared_entity", "No device in the bounded window connects multiple customers.")
    transaction_ids = [
        match["transaction_id"]
        for matches in qualifying_devices.values()
        for match in matches
    ]
    return _evidence(
        "shared_entity",
        "A shared device profile connects transactions from multiple customers in the bounded investigation window.",
        transaction_ids,
        confidence=min(0.99, 0.60 + 0.05 * len(connected_customers)),
        connected_card_ids=sorted(set(connected_cards)),
        shared_device_profiles=sorted(qualifying_devices),
        connected_customer_ids=sorted(set(connected_customers)),
    )


def detect_cnp(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    online = [transaction for transaction in transactions if transaction.get("channel") == "online"]
    if len(online) < 2:
        return _no_match("cnp", "Fewer than two online transactions were found in the 48-hour window.")
    ordered = sorted(online, key=lambda transaction: _timestamp(transaction["ts"]))
    ids = [transaction["TransactionID"] for transaction in ordered]
    return _evidence(
        "cnp",
        "Multiple online transactions occurred in the 48-hour investigation window.",
        ids,
        confidence=min(0.80, 0.50 + 0.05 * len(online)),
        online_transaction_count=len(online),
        window_hours=48,
    )


def detect_new_device(profile: dict[str, Any]) -> dict[str, Any]:
    flagged_id = profile["flagged_transaction"]["TransactionID"]
    identity = profile.get("identity", {}).get(flagged_id, {})
    if identity.get("id_15", "").strip().lower() != "new":
        return _no_match("cnp_new_device", "The flagged transaction is not marked as a new device for the account.")
    details = {
        "device_profile": profile.get("window_48h", {}).get("device_profiles", []),
        "device_status": identity.get("id_15", ""),
        "proxy_type": identity.get("id_23", ""),
    }
    return _evidence(
        "cnp_new_device",
        "The flagged online transaction was recorded from a device marked New for the account.",
        [flagged_id],
        confidence=0.75,
        **details,
    )


def detect_out_of_region(profile: dict[str, Any]) -> dict[str, Any]:
    transactions = sorted(profile["window_48h"].get("transactions", []), key=lambda item: _timestamp(item["ts"]))
    flagged = profile["flagged_transaction"]
    if flagged.get("channel") != "in_person" or not flagged.get("addr1"):
        return _no_match("out_of_region", "The flagged transaction is not an in-person transaction with a billing region.")
    prior_regions = {
        transaction.get("addr1")
        for transaction in transactions
        if transaction["TransactionID"] != flagged["TransactionID"]
        and transaction.get("channel") == "in_person"
        and transaction.get("addr1")
        and _timestamp(transaction["ts"]) <= _timestamp(flagged["ts"])
    }
    if not prior_regions or flagged["addr1"] in prior_regions:
        return _no_match("out_of_region", "No new billing region is established before the flagged transaction.")
    ids = [
        transaction["TransactionID"] for transaction in transactions
        if transaction.get("addr1") in prior_regions | {flagged["addr1"]}
    ]
    return _evidence(
        "out_of_region",
        "The flagged in-person transaction occurred in a region not seen earlier in the bounded customer window.",
        ids,
        confidence=0.60,
        flagged_region=flagged["addr1"],
        prior_regions=sorted(prior_regions),
    )


def detect_account_takeover(profile: dict[str, Any], new_device: dict[str, Any]) -> dict[str, Any]:
    transactions = profile["window_48h"].get("transactions", [])
    channels = {transaction.get("channel") for transaction in transactions}
    if not {"online", "in_person"}.issubset(channels) or not new_device["matched"]:
        return _no_match("account_takeover", "Mixed-channel activity and a new-device signal were not both present.")
    ids = [transaction["TransactionID"] for transaction in transactions]
    return _evidence(
        "account_takeover",
        "Mixed-channel activity coincides with a new device signal, warranting account-takeover review.",
        ids,
        confidence=0.65,
        channels=sorted(channels),
    )


def detect_undocumented(profile: dict[str, Any], shared_entity: dict[str, Any]) -> dict[str, Any]:
    transactions = sorted(
        (transaction for transaction in profile["window_48h"].get("transactions", []) if transaction.get("channel") == "online"),
        key=lambda transaction: _timestamp(transaction["ts"]),
    )
    for group in combinations(transactions, 4):
        if all(_amount(transaction) < STRUCTURING_LIMIT_USD for transaction in group):
            span = (_timestamp(group[-1]["ts"]) - _timestamp(group[0]["ts"])).total_seconds()
            if span <= STRUCTURING_WINDOW_SECONDS:
                return _evidence(
                    "undocumented",
                    "Four online purchases below $500 occurred within forty minutes, indicating possible structuring.",
                    [transaction["TransactionID"] for transaction in group],
                    confidence=0.85,
                    subtype="structuring_under_threshold",
                    window_seconds=round(span),
                )
    connected_customers = {
        customer_id
        for evidence in shared_entity.get("evidence", [])
        for customer_id in evidence.get("connected_customer_ids", [])
    }
    if shared_entity["matched"] and len(connected_customers) >= 3:
        return _evidence(
            "undocumented",
            "Coordinated activity across customers does not fit a single-card documented pattern.",
            shared_entity["transaction_ids"],
            confidence=0.90,
            subtype="shared_device_coordination",
            connected_card_ids=shared_entity["connected_card_ids"],
            connected_customer_count=len(connected_customers),
        )
    return _no_match(
        "undocumented",
        "No qualifying structuring sequence or multi-customer coordinated activity was found.",
    )


def detect_case(profile: dict[str, Any], shared_entities: dict[str, Any]) -> dict[str, Any]:
    transactions = profile["window_48h"].get("transactions", [])
    shared_entity = detect_shared_entity(profile["case_id"], shared_entities)
    new_device = detect_new_device(profile)
    detectors = [
        detect_card_testing(transactions),
        shared_entity,
        detect_cnp(transactions),
        new_device,
        detect_out_of_region(profile),
        detect_account_takeover(profile, new_device),
        detect_undocumented(profile, shared_entity),
    ]
    return {
        "case_id": profile["case_id"],
        "flagged_transaction_id": profile["flagged_transaction"]["TransactionID"],
        "detectors": detectors,
        "matched_patterns": [detector["pattern"] for detector in detectors if detector["matched"]],
    }


def detect_cases(profiles: list[dict[str, Any]], shared_entities: dict[str, Any]) -> list[dict[str, Any]]:
    return [detect_case(profile, shared_entities) for profile in profiles]