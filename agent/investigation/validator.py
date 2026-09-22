"""Validation for benchmark answer files.

The validator checks contract and policy consistency. It does not judge whether
the analyst's fraud conclusion is correct.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from agent.policy.actions import Action, Route


PATTERNS = {
    "card_testing",
    "card_not_present_fraud",
    "card_not_present_new_device",
    "out_of_region_use",
    "account_takeover",
    "undocumented",
    "none",
}
STATUSES = {"open", "closed_fraud", "closed_legitimate", "escalated"}
VERDICTS = {"fraud", "legitimate", "uncertain"}
SOURCES = {"graph", "document", "customer", "external"}
REQUEST_TYPES = {"customer_validation", "step_up_auth", "analyst_info"}
FLOAT_TOLERANCE = 0.02


@dataclass(frozen=True)
class DatasetIndex:
    transaction_amounts: dict[str, float]
    transaction_ids: set[str]
    card_ids: set[str]
    customer_ids: set[str]
    prior_case_ids: set[str]
    case_ids: set[str]


def _rows(path: Path):
    with path.open("r", newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def build_dataset_index(data_dir: Path, mapping_path: Path) -> DatasetIndex:
    transaction_amounts: dict[str, float] = {}
    customer_ids: set[str] = set()
    for row in _rows(data_dir / "transactions.csv"):
        transaction_id = row["TransactionID"]
        transaction_amounts[transaction_id] = abs(float(row["TransactionAmt"]))
        if row.get("customer_id"):
            customer_ids.add(row["customer_id"])

    card_ids = {row["card_id"] for row in _rows(mapping_path) if row.get("card_id")}
    case_rows = list(_rows(data_dir / "case_pack.csv"))
    case_ids = {row["case_id"] for row in case_rows}
    card_ids.update(row["card_id"] for row in case_rows if row.get("card_id"))
    customer_ids.update(row["customer_id"] for row in case_rows if row.get("customer_id"))
    prior_case_ids = {row["case_id"] for row in _rows(data_dir / "closed_cases_history.csv")}
    return DatasetIndex(
        transaction_amounts=transaction_amounts,
        transaction_ids=set(transaction_amounts),
        card_ids=card_ids,
        customer_ids=customer_ids,
        prior_case_ids=prior_case_ids,
        case_ids=case_ids,
    )


def _required(value: Any, path: str, errors: list[str]) -> None:
    if value is None:
        errors.append(f"{path}: missing")


def _datetime(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, str):
        errors.append(f"{path}: expected ISO date string")
        return
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{path}: invalid date '{value}'")


def _ids(values: Any, valid: set[str], path: str, errors: list[str]) -> None:
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        errors.append(f"{path}: expected list of strings")
        return
    for value in values:
        if value not in valid:
            errors.append(f"{path}: unknown id '{value}'")


def _actions(values: Any, path: str, errors: list[str]) -> None:
    if not isinstance(values, list):
        errors.append(f"{path}: expected list")
        return
    for index, item in enumerate(values):
        item_path = f"{path}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_path}: expected object")
            continue
        if item.get("action") not in {action.value for action in Action}:
            errors.append(f"{item_path}.action: invalid action")
        if item.get("route") not in {route.value for route in Route}:
            errors.append(f"{item_path}.route: invalid route")
        if not isinstance(item.get("reason"), str) or not item["reason"].upper().startswith("R"):
            errors.append(f"{item_path}.reason: must cite a policy rule")


def validate_answer(answer: dict[str, Any], index: DatasetIndex) -> list[str]:
    """Return validation errors; an empty list means the answer is valid."""
    errors: list[str] = []
    required_top = {"case_id", "case", "evidence_requests", "next_best_actions", "sar", "stop_reason", "tool_calls", "tokens", "latency_s"}
    errors.extend(f"top-level: missing '{key}'" for key in sorted(required_top - set(answer)))
    case_id = answer.get("case_id")
    if case_id not in index.case_ids:
        errors.append(f"case_id: unknown case '{case_id}'")
    case = answer.get("case")
    if not isinstance(case, dict):
        errors.append("case: expected object")
        return errors

    required_case = {
        "status", "verdict", "fraud_probability", "pattern", "pattern_description",
        "affected_txn_ids", "first_suspicious_txn_id", "connected_card_ids",
        "connected_device_profiles", "exposure_usd", "evidence", "similar_prior_cases",
        "summary", "written_to_graph", "graph_case_id",
    }
    errors.extend(f"case: missing '{key}'" for key in sorted(required_case - set(case)))
    if case.get("status") not in STATUSES:
        errors.append("case.status: invalid status")
    if case.get("verdict") not in VERDICTS:
        errors.append("case.verdict: invalid verdict")
    probability = case.get("fraud_probability")
    if not isinstance(probability, (int, float)) or isinstance(probability, bool) or not 0 <= probability <= 1:
        errors.append("case.fraud_probability: expected number from 0 to 1")
    pattern = case.get("pattern")
    if pattern not in PATTERNS:
        errors.append("case.pattern: invalid pattern")
    if pattern == "undocumented" and not case.get("pattern_description"):
        errors.append("case.pattern_description: required for undocumented pattern")
    if case.get("verdict") == "legitimate" and case.get("affected_txn_ids"):
        errors.append("case.affected_txn_ids: must be empty for legitimate verdict")

    affected_txn_ids = case.get("affected_txn_ids", [])
    connected_card_ids = case.get("connected_card_ids", [])
    similar_prior_cases = case.get("similar_prior_cases", [])
    _ids(affected_txn_ids, index.transaction_ids, "case.affected_txn_ids", errors)
    _ids(connected_card_ids, index.card_ids, "case.connected_card_ids", errors)
    _ids(similar_prior_cases, index.prior_case_ids, "case.similar_prior_cases", errors)
    first_id = case.get("first_suspicious_txn_id", "")
    if first_id and first_id not in index.transaction_ids:
        errors.append(f"case.first_suspicious_txn_id: unknown id '{first_id}'")

    expected_exposure = sum(index.transaction_amounts.get(txn_id, 0.0) for txn_id in affected_txn_ids if isinstance(txn_id, str))
    exposure = case.get("exposure_usd")
    if not isinstance(exposure, (int, float)) or not math.isclose(exposure, expected_exposure, abs_tol=FLOAT_TOLERANCE):
        errors.append(f"case.exposure_usd: expected {expected_exposure:.2f}, got {exposure}")
    if case.get("verdict") == "legitimate" and exposure != 0:
        errors.append("case.exposure_usd: must be zero for legitimate verdict")

    evidence = case.get("evidence")
    if not isinstance(evidence, list):
        errors.append("case.evidence: expected list")
    else:
        for evidence_index, item in enumerate(evidence):
            path = f"case.evidence[{evidence_index}]"
            if not isinstance(item, dict):
                errors.append(f"{path}: expected object")
                continue
            if not isinstance(item.get("claim"), str) or not item["claim"]:
                errors.append(f"{path}.claim: required")
            if item.get("source") not in SOURCES:
                errors.append(f"{path}.source: invalid source")
            if not isinstance(item.get("ref"), str) or not item["ref"]:
                errors.append(f"{path}.ref: required")
            if not isinstance(item.get("entity_ids"), list):
                errors.append(f"{path}.entity_ids: expected list")

    requests = answer.get("evidence_requests")
    if not isinstance(requests, list):
        errors.append("evidence_requests: expected list")
    else:
        for request_index, request in enumerate(requests):
            path = f"evidence_requests[{request_index}]"
            if not isinstance(request, dict):
                errors.append(f"{path}: expected object")
                continue
            if request.get("type") not in REQUEST_TYPES:
                errors.append(f"{path}.type: invalid request type")
            if not isinstance(request.get("asked_after_step"), int) or request["asked_after_step"] < 0:
                errors.append(f"{path}.asked_after_step: expected non-negative integer")
            if not isinstance(request.get("assumed_response"), str) or not request["assumed_response"]:
                errors.append(f"{path}.assumed_response: required")

    actions = answer.get("next_best_actions")
    if not isinstance(actions, dict):
        errors.append("next_best_actions: expected object")
    else:
        _actions(actions.get("initial"), "next_best_actions.initial", errors)
        _actions(actions.get("final"), "next_best_actions.final", errors)
        if not isinstance(actions.get("what_changed"), str) or not actions["what_changed"]:
            errors.append("next_best_actions.what_changed: required")
        if not requests and actions.get("initial") != actions.get("final"):
            errors.append("next_best_actions: final must equal initial when no evidence was requested")

        final_report = any(item.get("action") == Action.FILE_REPORT.value for item in actions.get("final", []))
        sar = answer.get("sar", {})
        if isinstance(sar, dict) and sar.get("file") != final_report:
            errors.append("sar.file: must agree with FILE_REPORT in final actions")

    sar = answer.get("sar")
    if not isinstance(sar, dict):
        errors.append("sar: expected object")
    else:
        for key in ("file", "reason", "narrative", "subjects", "total_amount_usd", "activity_dates"):
            _required(sar.get(key), f"sar.{key}", errors)
        if sar.get("file"):
            if not sar.get("narrative") or not sar.get("subjects") or len(sar.get("activity_dates", [])) != 2:
                errors.append("sar: filed report requires narrative, subjects, and two activity dates")
        elif sar.get("narrative") != "" or sar.get("subjects") != [] or sar.get("total_amount_usd") != 0 or sar.get("activity_dates") != []:
            errors.append("sar: non-filed report must have empty narrative, subjects, amount, and dates")

    for field in ("stop_reason",):
        if not isinstance(answer.get(field), str) or not answer[field]:
            errors.append(f"{field}: required")
    for field in ("tool_calls", "tokens"):
        if not isinstance(answer.get(field), int) or answer[field] < 0:
            errors.append(f"{field}: expected non-negative integer")
    if not isinstance(answer.get("latency_s"), (int, float)) or answer["latency_s"] < 0:
        errors.append("latency_s: expected non-negative number")
    return errors