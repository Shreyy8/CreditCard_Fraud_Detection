"""Compose a deterministic draft answer from local evidence artifacts."""

from __future__ import annotations

from typing import Any

from agent.policy import CaseContext, evaluate


def _matched(result: dict[str, Any], pattern: str) -> dict[str, Any] | None:
    return next((item for item in result["detectors"] if item["pattern"] == pattern and item["matched"]), None)


def _select_pattern(result: dict[str, Any]) -> str:
    priority = (
        ("undocumented", "undocumented"),
        ("card_testing", "card_testing"),
        ("cnp_new_device", "card_not_present_new_device"),
        ("account_takeover", "account_takeover"),
        ("out_of_region", "out_of_region_use"),
        ("cnp", "card_not_present_fraud"),
    )
    for detector_name, answer_pattern in priority:
        if _matched(result, detector_name):
            return answer_pattern
    return "none"


def _probability(pattern: str, profile: dict[str, Any], detector_result: dict[str, Any]) -> float:
    trigger_type = profile["trigger"]["trigger_type"]
    if pattern == "undocumented":
        return 0.90
    if trigger_type == "customer_report":
        return 0.85
    if pattern in {"card_testing", "account_takeover"}:
        return 0.82
    if pattern == "card_not_present_new_device":
        return 0.72
    if pattern == "out_of_region_use":
        return 0.55
    if pattern == "card_not_present_fraud":
        return 0.60
    return float(profile["flagged_transaction"].get("risk_score") or 0.50)


def _action_dicts(policy_result) -> list[dict[str, Any]]:
    return [
        {
            "action": recommendation.action.value,
            "route": recommendation.route.value,
            "reason": recommendation.reason,
        }
        for recommendation in policy_result.actions
    ]


def _context(
    *,
    verdict: str,
    probability: float,
    exposure: float,
    matched_count: int,
    pattern: str,
    shared_type: dict[str, Any] | None,
    coordinated: bool,
    customer_response: str | None,
) -> CaseContext:
    return CaseContext(
        verdict=verdict,
        fraud_probability=probability,
        evidence_count=max(1, matched_count),
        exposure_usd=exposure,
        is_single_signal=matched_count <= 1,
        customer_response=customer_response,
        pattern="card_testing" if pattern == "card_testing" else None,
        shared_entity=shared_type,
        recurring_match=False,
        coordinated_undocumented=coordinated,
        confirmed_fraud_card_count=0,
        credentials_confirmed_compromised=False,
        large_purchase_cleared=pattern == "card_testing" and exposure > 100,
        evidence_conflicts=False,
    )


def _simulated_request(profile: dict[str, Any], probability: float, pattern: str) -> tuple[dict[str, Any] | None, str | None]:
    trigger_type = profile["trigger"]["trigger_type"]
    if trigger_type == "customer_report":
        return {
            "type": "customer_validation",
            "asked_after_step": 4,
            "assumed_response": "Customer denies making the transaction and reports it as unauthorized.",
        }, "denied"
    if probability < 0.70 and pattern != "undocumented":
        return {
            "type": "customer_validation",
            "asked_after_step": 4,
            "assumed_response": "No customer reply within 24 hours; simulation uses the policy no_reply branch.",
        }, "no_reply"
    return None, None


def compose_answer(profile: dict[str, Any], detector_result: dict[str, Any]) -> dict[str, Any]:
    pattern = _select_pattern(detector_result)
    matched = next(
        (item for item in detector_result["detectors"] if item["pattern"] == "undocumented" and item["matched"]),
        None,
    )
    if matched is None:
        matched = next((item for item in detector_result["detectors"] if item["matched"]), None)
    affected_ids = sorted({
        transaction_id
        for transaction_id in (matched or {}).get("transaction_ids", [])
        if transaction_id in {
            transaction["TransactionID"]
            for transaction in profile["window_48h"].get("transactions", [])
        }
    })
    flagged_id = profile["flagged_transaction"]["TransactionID"]
    if pattern != "none" and flagged_id not in affected_ids:
        affected_ids.append(flagged_id)

    transaction_by_id = {
        item["TransactionID"]: item for item in profile["window_48h"].get("transactions", [])
    }
    exposure = round(sum(abs(float(transaction_by_id[item]["TransactionAmt"])) for item in affected_ids if item in transaction_by_id), 2)
    probability = _probability(pattern, profile, detector_result)
    connected_cards = sorted(set((matched or {}).get("connected_card_ids", [])))
    shared = _matched(detector_result, "shared_entity")
    if shared:
        connected_cards = sorted(set(connected_cards) | set(shared["connected_card_ids"]))
    shared_type = {"type": "device", "connected_card_ids": connected_cards} if shared else None
    verdict = "fraud" if probability >= 0.85 else "uncertain"
    if pattern == "none":
        verdict = "uncertain"
    coordinated = pattern == "undocumented"
    matched_count = len([item for item in detector_result["detectors"] if item["matched"]])
    initial_result = evaluate(_context(
        verdict=verdict,
        probability=probability,
        exposure=exposure,
        matched_count=matched_count,
        pattern=pattern,
        shared_type=shared_type,
        coordinated=coordinated,
        customer_response=None,
    ))
    request, response = _simulated_request(profile, probability, pattern)
    final_result = initial_result if response is None else evaluate(_context(
        verdict="fraud" if response == "denied" else verdict,
        probability=max(probability, 0.86) if response == "denied" else probability,
        exposure=exposure,
        matched_count=matched_count,
        pattern=pattern,
        shared_type=shared_type,
        coordinated=coordinated,
        customer_response=response,
    ))
    evidence = []
    for detector in detector_result["detectors"]:
        if detector["matched"]:
            evidence.extend({
                "claim": item["claim"],
                "source": "graph",
                "ref": f"detector:{detector['pattern']}",
                "entity_ids": detector["transaction_ids"],
            } for item in detector["evidence"])
    sar_file = any(item.action.value == "FILE_REPORT" for item in final_result.actions)
    dates = sorted(transaction_by_id[item]["ts"][:10] for item in affected_ids if item in transaction_by_id)
    summary = f"Local detectors found pattern {pattern} for flagged transaction {flagged_id}. Evidence includes {len(affected_ids)} affected transaction(s) and {len(connected_cards)} connected card(s)."
    return {
        "case_id": profile["case_id"],
        "case": {
            "status": "closed_fraud" if verdict == "fraud" else "open",
            "verdict": verdict,
            "fraud_probability": probability,
            "pattern": pattern,
            "pattern_description": "Coordinated activity across multiple customers sharing a device profile." if pattern == "undocumented" else "",
            "affected_txn_ids": affected_ids if verdict != "legitimate" else [],
            "first_suspicious_txn_id": affected_ids[0] if affected_ids else "",
            "connected_card_ids": connected_cards,
            "connected_device_profiles": profile["window_48h"].get("device_profiles", []) if shared else [],
            "exposure_usd": exposure if verdict != "legitimate" else 0,
            "evidence": evidence,
            "similar_prior_cases": [item["case_id"] for item in profile.get("similar_prior_cases", [])],
            "summary": summary,
            "written_to_graph": False,
            "graph_case_id": "",
        },
        "evidence_requests": [request] if request else [],
        "next_best_actions": {
            "initial": _action_dicts(initial_result),
            "final": _action_dicts(final_result),
            "what_changed": "The simulated evidence response changed the policy branch and final recommendation." if request else "nothing",
        },
        "sar": {
            "file": sar_file,
            "reason": "R9: coordinated undocumented activity requires a report" if sar_file else "No policy rule requires a suspicious activity report at this stage.",
            "narrative": summary if sar_file else "",
            "subjects": [profile["trigger"]["customer_id"], profile["trigger"]["card_id"], *connected_cards] if sar_file else [],
            "total_amount_usd": exposure if sar_file else 0,
            "activity_dates": [dates[0], dates[-1]] if sar_file and dates else [],
        },
        "stop_reason": final_result.stop_reason or "Further evidence is required before a policy stop threshold is met.",
        "tool_calls": len(detector_result["detectors"]),
        "tokens": 0,
        "latency_s": 0.0,
    }