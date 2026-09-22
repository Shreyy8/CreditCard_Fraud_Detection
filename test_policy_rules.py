"""
tests/test_policy_rules.py

Test-first spec for the policy engine (README section 10). Write
`agent/policy/actions.py`, `agent/policy/rules.py`, `agent/policy/router.py`
and `agent/policy/reporting.py` to make these pass -- don't change the tests
to match a different interface without updating README section 10 first,
since the rule numbers here are taken directly from Fraud Policy v1.0.

Interface this file assumes (adjust names to match your real `agent/state.py`
if it already exists, but keep the FIELDS, since each one maps to a specific
rule condition):

    from agent.policy.actions import Action, Route
    from agent.policy.engine import evaluate, CaseContext

    ctx = CaseContext(
        verdict="fraud" | "legitimate" | "uncertain",
        fraud_probability=0.0,          # 0-1
        evidence_count=0,               # number of INDEPENDENT evidence items
        exposure_usd=0.0,
        is_single_signal=False,         # True if the case rests on one signal only (incl. risk score alone)
        customer_response=None,         # None | "confirmed" | "denied" | "no_reply"
        pattern=None,                   # one of the 6 pattern strings, or None
        shared_entity=None,             # {"type": "device"|"region"|"email", "connected_card_ids": [...]}
        recurring_match=False,          # customer disputes a charge matching their own recurring pattern (R7)
        coordinated_undocumented=False, # fits no known pattern but shows coordinated/repeated abuse (R9)
        confirmed_fraud_card_count=0,   # how many of the customer's OTHER cards already show confirmed fraud (R10)
        credentials_confirmed_compromised=False,  # R10
    )
    result = evaluate(ctx)   # -> PolicyResult(actions=[ActionRec(action, route, reason), ...], stop=bool, stop_reason=str|None)

Each `ActionRec.reason` MUST start with the rule id it satisfies, e.g. "R1: ...",
so `tests/test_answer_schema.py` and the README's answer-file validator can
grep for it. Reasons for guardrail-only actions (R10) may cite "R10" or state
the guardrail was NOT triggered.
"""

from __future__ import annotations

import pytest

from agent.policy.actions import Action, Route
from agent.policy.engine import evaluate, CaseContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def base_ctx(**overrides) -> CaseContext:
    """A minimal, otherwise-inert case context. Override only what a test needs."""
    defaults = dict(
        verdict="uncertain",
        fraud_probability=0.5,
        evidence_count=1,
        exposure_usd=0.0,
        is_single_signal=True,
        customer_response=None,
        pattern=None,
        shared_entity=None,
        recurring_match=False,
        coordinated_undocumented=False,
        confirmed_fraud_card_count=0,
        credentials_confirmed_compromised=False,
    )
    defaults.update(overrides)
    return CaseContext(**defaults)


def actions_of(result) -> set[Action]:
    return {rec.action for rec in result.actions}


def route_of(result, action: Action) -> Route:
    matches = [rec.route for rec in result.actions if rec.action == action]
    assert matches, f"{action} not found in result.actions"
    return matches[0]


def reasons_cite(result, action: Action, rule_id: str) -> bool:
    return any(
        rec.action == action and rec.reason.upper().startswith(rule_id.upper())
        for rec in result.actions
    )


# ---------------------------------------------------------------------------
# R1: single signal, probability < 0.70 -> verify before any block
# ---------------------------------------------------------------------------

class TestR1SingleSignalRequiresVerification:

    def test_single_signal_below_threshold_recommends_verification(self):
        ctx = base_ctx(is_single_signal=True, fraud_probability=0.45, verdict="uncertain")
        result = evaluate(ctx)
        acts = actions_of(result)
        assert Action.VERIFY_WITH_CUSTOMER in acts or Action.STEP_UP_AUTH in acts
        assert Action.BLOCK_CARD not in acts
        assert Action.DECLINE_TRANSACTION not in acts

    def test_single_signal_below_threshold_never_blocks_outright(self):
        ctx = base_ctx(is_single_signal=True, fraud_probability=0.69, verdict="uncertain")
        result = evaluate(ctx)
        assert Action.BLOCK_CARD not in actions_of(result)

    def test_single_signal_at_or_above_070_is_exempt_from_r1(self):
        # 0.70 is the documented exemption threshold -- at or above it, R1 no
        # longer forces a verification step first.
        ctx = base_ctx(is_single_signal=True, fraud_probability=0.70, verdict="fraud",
                        evidence_count=1)
        result = evaluate(ctx)
        # Not asserting BLOCK_CARD is present here (that depends on other
        # rules/evidence independence for the stop rule) -- only that R1's
        # forced-verification-first constraint no longer applies.
        assert reasons_cite(result, Action.VERIFY_WITH_CUSTOMER, "R1") is False \
            or Action.VERIFY_WITH_CUSTOMER not in actions_of(result)

    def test_multi_signal_below_070_is_not_bound_by_r1(self):
        ctx = base_ctx(is_single_signal=False, fraud_probability=0.45, verdict="uncertain",
                        evidence_count=3)
        result = evaluate(ctx)
        # R1 specifically targets single-signal cases; multi-signal cases at
        # the same probability may still choose to verify, but it must not
        # be because R1 forced it.
        assert reasons_cite(result, Action.VERIFY_WITH_CUSTOMER, "R1") is False


# ---------------------------------------------------------------------------
# R2 / R3 / R4: customer response branches
# ---------------------------------------------------------------------------

class TestR2CustomerDenies:

    def test_denial_blocks_card_and_creates_case(self):
        ctx = base_ctx(customer_response="denied", verdict="fraud", fraud_probability=0.8,
                        exposure_usd=200.0)
        result = evaluate(ctx)
        acts = actions_of(result)
        assert Action.BLOCK_CARD in acts
        assert Action.CREATE_CASE in acts

    def test_denial_with_exposure_over_1000_files_report(self):
        ctx = base_ctx(customer_response="denied", verdict="fraud", fraud_probability=0.8,
                        exposure_usd=1500.0)
        result = evaluate(ctx)
        assert Action.FILE_REPORT in actions_of(result)

    def test_denial_with_low_exposure_and_no_shared_entity_does_not_file_report(self):
        ctx = base_ctx(customer_response="denied", verdict="fraud", fraud_probability=0.8,
                        exposure_usd=50.0, shared_entity=None)
        result = evaluate(ctx)
        assert Action.FILE_REPORT not in actions_of(result)

    def test_denial_connected_to_shared_device_files_report_regardless_of_exposure(self):
        ctx = base_ctx(customer_response="denied", verdict="fraud", fraud_probability=0.8,
                        exposure_usd=20.0,
                        shared_entity={"type": "device", "connected_card_ids": ["C00001-K1", "C00002-K1"]})
        result = evaluate(ctx)
        assert Action.FILE_REPORT in actions_of(result)


class TestR3CustomerConfirms:

    def test_confirmation_closes_case_no_fraud(self):
        ctx = base_ctx(customer_response="confirmed", verdict="uncertain", fraud_probability=0.5)
        result = evaluate(ctx)
        acts = actions_of(result)
        assert Action.CLOSE_NO_FRAUD in acts
        assert Action.BLOCK_CARD not in acts
        assert Action.FILE_REPORT not in acts


class TestR4NoReply:

    def test_no_reply_monitors_and_declines_pending(self):
        ctx = base_ctx(customer_response="no_reply", verdict="uncertain", fraud_probability=0.5,
                        exposure_usd=100.0)
        result = evaluate(ctx)
        acts = actions_of(result)
        assert Action.MONITOR_CARD in acts
        assert Action.DECLINE_TRANSACTION in acts

    def test_no_reply_with_high_exposure_escalates(self):
        ctx = base_ctx(customer_response="no_reply", verdict="uncertain", fraud_probability=0.5,
                        exposure_usd=750.0)
        result = evaluate(ctx)
        assert Action.ESCALATE_TO_ANALYST in actions_of(result)

    def test_no_reply_with_low_exposure_does_not_escalate(self):
        ctx = base_ctx(customer_response="no_reply", verdict="uncertain", fraud_probability=0.5,
                        exposure_usd=100.0)
        result = evaluate(ctx)
        assert Action.ESCALATE_TO_ANALYST not in actions_of(result)


# ---------------------------------------------------------------------------
# R5: card testing
# ---------------------------------------------------------------------------

class TestR5CardTesting:

    def test_card_testing_pattern_declines_and_requires_step_up(self):
        ctx = base_ctx(pattern="card_testing", verdict="fraud", fraud_probability=0.75,
                        evidence_count=2, is_single_signal=False)
        result = evaluate(ctx)
        acts = actions_of(result)
        assert Action.DECLINE_TRANSACTION in acts
        assert Action.STEP_UP_AUTH in acts

    def test_card_testing_with_cleared_large_purchase_blocks_card(self, ):
        # A purchase over $100 already cleared -> escalate to BLOCK_CARD.
        # Signalled via exposure_usd representing the cleared purchase amount
        # plus a context flag; adjust field name to match your real
        # CaseContext if it differs (e.g. `large_purchase_cleared: bool`).
        ctx = base_ctx(pattern="card_testing", verdict="fraud", fraud_probability=0.85,
                        evidence_count=2, is_single_signal=False, exposure_usd=150.0)
        ctx = ctx._replace(large_purchase_cleared=True) if hasattr(ctx, "_replace") else ctx
        result = evaluate(ctx)
        assert Action.BLOCK_CARD in actions_of(result)


# ---------------------------------------------------------------------------
# R6: shared device / region / email ring
# ---------------------------------------------------------------------------

class TestR6SharedEntityRing:

    def test_shared_device_ring_creates_case_files_report_and_monitors_connected_cards(self):
        ctx = base_ctx(
            verdict="fraud", fraud_probability=0.9, evidence_count=3, is_single_signal=False,
            shared_entity={
                "type": "device",
                "connected_card_ids": ["C00001-K1", "C00002-K1", "C00003-K1"],
            },
        )
        result = evaluate(ctx)
        acts = actions_of(result)
        assert Action.CREATE_CASE in acts
        assert Action.FILE_REPORT in acts
        assert Action.MONITOR_CONNECTED_CARDS in acts

    def test_shared_entity_type_is_named_in_reason(self):
        ctx = base_ctx(
            verdict="fraud", fraud_probability=0.9, evidence_count=3, is_single_signal=False,
            shared_entity={"type": "region", "connected_card_ids": ["C00009-K1"]},
        )
        result = evaluate(ctx)
        monitor_recs = [r for r in result.actions if r.action == Action.MONITOR_CONNECTED_CARDS]
        assert monitor_recs, "expected a MONITOR_CONNECTED_CARDS recommendation"
        assert "region" in monitor_recs[0].reason.lower()


# ---------------------------------------------------------------------------
# R7: recurring charge dispute -> never block
# ---------------------------------------------------------------------------

class TestR7RecurringChargeDispute:

    def test_recurring_match_creates_case_and_verifies_but_never_blocks(self):
        ctx = base_ctx(recurring_match=True, customer_response="denied",
                        verdict="uncertain", fraud_probability=0.4, exposure_usd=40.0)
        result = evaluate(ctx)
        acts = actions_of(result)
        assert Action.CREATE_CASE in acts
        assert Action.VERIFY_WITH_CUSTOMER in acts
        assert Action.WARN_CUSTOMER in acts
        assert Action.BLOCK_CARD not in acts
        assert Action.DECLINE_TRANSACTION not in acts

    def test_recurring_match_overrides_r2_block_even_on_denial(self):
        # This is the key interaction test: R2 alone would block on a denial,
        # but R7 must take precedence when the disputed charge matches the
        # customer's own recurring pattern.
        ctx = base_ctx(recurring_match=True, customer_response="denied",
                        verdict="fraud", fraud_probability=0.8, exposure_usd=2000.0)
        result = evaluate(ctx)
        assert Action.BLOCK_CARD not in actions_of(result)


# ---------------------------------------------------------------------------
# R8: uncertain + exposure > $500, or conflicting evidence -> escalate
# ---------------------------------------------------------------------------

class TestR8EscalateOnUncertainty:

    def test_uncertain_high_exposure_escalates(self):
        ctx = base_ctx(verdict="uncertain", fraud_probability=0.5, exposure_usd=600.0)
        result = evaluate(ctx)
        assert Action.ESCALATE_TO_ANALYST in actions_of(result)

    def test_uncertain_low_exposure_does_not_require_escalation(self):
        ctx = base_ctx(verdict="uncertain", fraud_probability=0.5, exposure_usd=100.0)
        result = evaluate(ctx)
        # Not escalating is fine at low exposure -- R8's condition is exposure > $500 OR conflicting evidence.
        assert Action.ESCALATE_TO_ANALYST not in actions_of(result)

    def test_conflicting_evidence_escalates_even_at_low_exposure(self):
        # `evidence_count` alone doesn't encode conflict; if your CaseContext
        # tracks it differently (e.g. an `evidence_conflicts: bool` field),
        # update this test to match -- the requirement is the behavior below.
        ctx = base_ctx(verdict="uncertain", fraud_probability=0.5, exposure_usd=50.0)
        ctx_with_conflict = ctx._replace(evidence_conflicts=True) if hasattr(ctx, "_replace") else ctx
        result = evaluate(ctx_with_conflict)
        assert Action.ESCALATE_TO_ANALYST in actions_of(result)


# ---------------------------------------------------------------------------
# R9: undocumented, coordinated pattern
# ---------------------------------------------------------------------------

class TestR9UndocumentedCoordinatedPattern:

    def test_coordinated_undocumented_creates_case_files_report_and_escalates(self):
        ctx = base_ctx(pattern=None, coordinated_undocumented=True,
                        verdict="fraud", fraud_probability=0.8, evidence_count=3,
                        is_single_signal=False)
        result = evaluate(ctx)
        acts = actions_of(result)
        assert Action.CREATE_CASE in acts
        assert Action.FILE_REPORT in acts
        assert Action.ESCALATE_TO_ANALYST in acts

    def test_undocumented_does_not_force_a_known_pattern_label(self):
        # The pattern field should remain None/undocumented, not coerced
        # into one of the 5 documented categories. This is really an
        # assessment-layer test (agent/assess.py), included here as a
        # policy-layer sanity check that R9 doesn't require `pattern` to be set.
        ctx = base_ctx(pattern=None, coordinated_undocumented=True,
                        verdict="fraud", fraud_probability=0.8, evidence_count=3,
                        is_single_signal=False)
        result = evaluate(ctx)  # should not raise
        assert result is not None


# ---------------------------------------------------------------------------
# R10: BLOCK_ALL_CARDS guardrail
# ---------------------------------------------------------------------------

class TestR10BlockAllCardsGuardrail:

    def test_block_all_cards_not_recommended_by_default(self):
        ctx = base_ctx(verdict="fraud", fraud_probability=0.95, evidence_count=3,
                        is_single_signal=False, exposure_usd=5000.0)
        result = evaluate(ctx)
        assert Action.BLOCK_ALL_CARDS not in actions_of(result)

    def test_block_all_cards_allowed_with_two_confirmed_fraud_cards(self):
        ctx = base_ctx(verdict="fraud", fraud_probability=0.95, evidence_count=3,
                        is_single_signal=False, confirmed_fraud_card_count=2)
        result = evaluate(ctx)
        assert Action.BLOCK_ALL_CARDS in actions_of(result)

    def test_block_all_cards_allowed_with_compromised_credentials(self):
        ctx = base_ctx(verdict="fraud", fraud_probability=0.95, evidence_count=3,
                        is_single_signal=False, credentials_confirmed_compromised=True)
        result = evaluate(ctx)
        assert Action.BLOCK_ALL_CARDS in actions_of(result)

    def test_block_all_cards_never_appears_from_a_single_flagged_card_alone(self):
        # Regression guard: even a very high probability, high-exposure,
        # single-card case must never trigger BLOCK_ALL_CARDS without R10's
        # explicit condition.
        ctx = base_ctx(verdict="fraud", fraud_probability=0.99, evidence_count=5,
                        is_single_signal=False, exposure_usd=50000.0,
                        confirmed_fraud_card_count=0, credentials_confirmed_compromised=False)
        result = evaluate(ctx)
        assert Action.BLOCK_ALL_CARDS not in actions_of(result)


# ---------------------------------------------------------------------------
# Approval routes (section 10.1)
# ---------------------------------------------------------------------------

class TestApprovalRoutes:

    @pytest.mark.parametrize("action", [
        Action.ALLOW_TRANSACTION, Action.MONITOR_CARD, Action.MONITOR_CONNECTED_CARDS,
        Action.WARN_CUSTOMER, Action.VERIFY_WITH_CUSTOMER, Action.STEP_UP_AUTH,
        Action.GENERATE_REPORT, Action.CREATE_CASE, Action.ESCALATE_TO_ANALYST,
        Action.CLOSE_NO_FRAUD,
    ])
    def test_auto_actions_route_auto(self, action):
        from agent.policy.router import route_for_action
        assert route_for_action(action, exposure_usd=1.0) == Route.AUTO
        assert route_for_action(action, exposure_usd=10_000.0) == Route.AUTO

    def test_decline_transaction_routes_l1(self):
        from agent.policy.router import route_for_action
        assert route_for_action(Action.DECLINE_TRANSACTION, exposure_usd=50.0) == Route.L1

    def test_block_card_routes_l1_at_or_below_2500(self):
        from agent.policy.router import route_for_action
        assert route_for_action(Action.BLOCK_CARD, exposure_usd=2500.0) == Route.L1
        assert route_for_action(Action.BLOCK_CARD, exposure_usd=100.0) == Route.L1

    def test_block_card_routes_l2_above_2500(self):
        from agent.policy.router import route_for_action
        assert route_for_action(Action.BLOCK_CARD, exposure_usd=2500.01) == Route.L2
        assert route_for_action(Action.BLOCK_CARD, exposure_usd=10_000.0) == Route.L2

    def test_block_all_cards_always_routes_l2(self):
        from agent.policy.router import route_for_action
        assert route_for_action(Action.BLOCK_ALL_CARDS, exposure_usd=1.0) == Route.L2
        assert route_for_action(Action.BLOCK_ALL_CARDS, exposure_usd=1_000_000.0) == Route.L2

    def test_file_report_always_routes_l2(self):
        from agent.policy.router import route_for_action
        assert route_for_action(Action.FILE_REPORT, exposure_usd=1.0) == Route.L2

    def test_every_actionrec_from_evaluate_has_a_route_matching_the_table(self):
        from agent.policy.router import route_for_action
        ctx = base_ctx(customer_response="denied", verdict="fraud", fraud_probability=0.9,
                        exposure_usd=3000.0,
                        shared_entity={"type": "device", "connected_card_ids": ["C00001-K1"]})
        result = evaluate(ctx)
        for rec in result.actions:
            assert rec.route == route_for_action(rec.action, ctx.exposure_usd), (
                f"{rec.action} routed as {rec.route}, expected "
                f"{route_for_action(rec.action, ctx.exposure_usd)}"
            )


# ---------------------------------------------------------------------------
# Case vs report criteria (section 10.3 / Policy 3a)
# ---------------------------------------------------------------------------

class TestCaseVsReportCriteria:

    def test_case_created_when_probability_reaches_030(self):
        ctx = base_ctx(verdict="uncertain", fraud_probability=0.30, is_single_signal=False)
        result = evaluate(ctx)
        assert Action.CREATE_CASE in actions_of(result)

    def test_case_not_created_below_030_with_no_other_trigger(self):
        ctx = base_ctx(verdict="legitimate", fraud_probability=0.10, is_single_signal=False,
                        customer_response=None, recurring_match=False)
        result = evaluate(ctx)
        assert Action.CREATE_CASE not in actions_of(result)

    def test_case_created_when_evidence_was_requested_even_below_030(self):
        # Requesting evidence (customer_response set to any branch implies a
        # request was made and answered) opens a case regardless of probability.
        ctx = base_ctx(verdict="uncertain", fraud_probability=0.15, customer_response="confirmed")
        result = evaluate(ctx)
        # Confirmed closes as no-fraud, but the case record itself should
        # still exist per Policy 3a ("or a customer disputes a charge").
        assert Action.CREATE_CASE in actions_of(result) or Action.CLOSE_NO_FRAUD in actions_of(result)

    def test_report_never_filed_without_a_case(self):
        ctx = base_ctx(verdict="fraud", fraud_probability=0.9, exposure_usd=5000.0,
                        is_single_signal=False)
        result = evaluate(ctx)
        acts = actions_of(result)
        if Action.FILE_REPORT in acts:
            assert Action.CREATE_CASE in acts

    def test_most_low_exposure_single_card_fraud_does_not_file_report(self):
        ctx = base_ctx(verdict="fraud", fraud_probability=0.8, exposure_usd=200.0,
                        is_single_signal=False, shared_entity=None, coordinated_undocumented=False)
        result = evaluate(ctx)
        assert Action.FILE_REPORT not in actions_of(result)


# ---------------------------------------------------------------------------
# Stop rules (section 10.5 / Policy section 6)
# ---------------------------------------------------------------------------

class TestStopRules:

    def test_stops_when_probability_above_085_with_two_independent_evidence(self):
        ctx = base_ctx(fraud_probability=0.9, evidence_count=2, verdict="fraud",
                        is_single_signal=False)
        result = evaluate(ctx)
        assert result.stop is True
        assert result.stop_reason

    def test_stops_when_probability_below_015_with_two_independent_evidence(self):
        ctx = base_ctx(fraud_probability=0.1, evidence_count=2, verdict="legitimate",
                        is_single_signal=False)
        result = evaluate(ctx)
        assert result.stop is True

    def test_does_not_stop_on_extreme_probability_with_only_one_evidence_item(self):
        # High/low probability alone isn't enough -- section 6 requires at
        # least two INDEPENDENT evidence items too.
        ctx = base_ctx(fraud_probability=0.95, evidence_count=1, verdict="fraud",
                        is_single_signal=True)
        result = evaluate(ctx)
        assert result.stop is False

    def test_does_not_stop_in_the_ambiguous_middle_with_no_response_yet(self):
        ctx = base_ctx(fraud_probability=0.5, evidence_count=2, verdict="uncertain",
                        customer_response=None)
        result = evaluate(ctx)
        assert result.stop is False

    def test_stops_once_customer_response_settles_the_question(self):
        ctx = base_ctx(fraud_probability=0.5, evidence_count=1, verdict="uncertain",
                        customer_response="confirmed")
        result = evaluate(ctx)
        assert result.stop is True


# ---------------------------------------------------------------------------
# Every recommendation cites a rule number (Policy section 7)
# ---------------------------------------------------------------------------

class TestReasonsCiteRuleNumbers:

    @pytest.mark.parametrize("ctx_kwargs", [
        dict(customer_response="denied", verdict="fraud", fraud_probability=0.8, exposure_usd=1500.0),
        dict(customer_response="confirmed", verdict="uncertain", fraud_probability=0.5),
        dict(pattern="card_testing", verdict="fraud", fraud_probability=0.75, is_single_signal=False),
        dict(verdict="uncertain", fraud_probability=0.5, exposure_usd=600.0),
    ])
    def test_every_action_has_a_rule_cited_reason(self, ctx_kwargs):
        ctx = base_ctx(**ctx_kwargs)
        result = evaluate(ctx)
        for rec in result.actions:
            assert rec.reason, f"{rec.action} has no reason"
            assert rec.reason.strip()[0:1] == "R" or "guardrail" in rec.reason.lower(), (
                f"{rec.action} reason does not cite a rule: {rec.reason!r}"
            )


# ---------------------------------------------------------------------------
# LLM-proposed actions must be validated, never trusted (section 10.6)
# ---------------------------------------------------------------------------

class TestEnforcementNotTrust:

    def test_evaluate_ignores_an_out_of_schema_action_string_if_passed_through(self):
        # If your engine's real entry point accepts "LLM-proposed actions" as
        # an input to validate/correct (rather than only computing from
        # CaseContext), adjust this test to call that function directly.
        # The requirement either way: an invented action name must never
        # reach the final action list.
        ctx = base_ctx(verdict="fraud", fraud_probability=0.8, is_single_signal=False)
        result = evaluate(ctx)
        valid_actions = set(Action)
        assert all(rec.action in valid_actions for rec in result.actions)

    def test_l2_action_is_recommended_not_marked_executed(self):
        ctx = base_ctx(customer_response="denied", verdict="fraud", fraud_probability=0.9,
                        exposure_usd=5000.0)
        result = evaluate(ctx)
        block_recs = [r for r in result.actions if r.action == Action.BLOCK_CARD]
        assert block_recs
        assert block_recs[0].route == Route.L2
        # An L2 route must never be silently auto-executed by the agent --
        # that's enforced in agent/case.py, but the route itself is the
        # signal it depends on, so pin it here too.
        assert getattr(block_recs[0], "executed", False) is False
