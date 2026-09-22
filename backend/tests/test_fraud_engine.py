"""
Tests for fraud engine components:
- RiskEngine
- PatternDetector
- ExposureEngine
- PolicyEngine
"""

import pytest
from app.fraud.risk_engine import RiskEngine
from app.fraud.pattern_detector import PatternDetector
from app.fraud.exposure_engine import ExposureEngine
from app.policy.policy_engine import PolicyEngine
from app.models.case import FraudPattern, ActionType, ApprovalRoute


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def base_txn():
    return {
        "TransactionID": "T001",
        "TransactionAmt": 100.0,
        "channel": "online",
        "ProductCD": "H",
        "card4": "visa",
        "card6": "credit",
        "addr1": "444",
        "addr2": "87",
        "P_emaildomain": "gmail.com",
        "ts": "2016-12-05 01:55:28",
        "risk_score": "0.61",
    }


@pytest.fixture
def history_txns():
    return [
        {"TransactionID": f"T00{i}", "TransactionAmt": 50.0 + i,
         "channel": "online", "addr2": "87", "ts": f"2016-11-0{i+1} 10:00:00"}
        for i in range(10)
    ]


# ── RiskEngine ────────────────────────────────────────────────────────────────

class TestRiskEngine:
    def test_customer_report_raises_risk(self, base_txn, history_txns):
        engine = RiskEngine()
        result = engine.assess(
            trigger_type="customer_report",
            bank_risk_score=0.6,
            txn=base_txn,
            customer_history=history_txns,
            identity=None,
            closed_cases=[],
            connected_cards=[],
            shared_devices=[],
            behavioral_anomalies=[],
        )
        assert result.risk_score > 0.5
        assert "customer_dispute" in [s.name for s in result.signals if s.triggered]

    def test_low_risk_score_with_no_signals(self, base_txn, history_txns):
        engine = RiskEngine()
        result = engine.assess(
            trigger_type="risk_score",
            bank_risk_score=0.2,
            txn=base_txn,
            customer_history=history_txns,
            identity=None,
            closed_cases=[],
            connected_cards=[],
            shared_devices=[],
            behavioral_anomalies=[],
        )
        assert result.risk_level in ("LOW", "MEDIUM")

    def test_new_device_adds_signal(self, base_txn, history_txns):
        engine = RiskEngine()
        identity = {"id_15": "New", "id_23": ""}
        result = engine.assess(
            trigger_type="risk_score",
            bank_risk_score=0.5,
            txn=base_txn,
            customer_history=history_txns,
            identity=identity,
            closed_cases=[],
            connected_cards=[],
            shared_devices=[],
            behavioral_anomalies=[],
        )
        assert any(s.name == "new_device" and s.triggered for s in result.signals)

    def test_prior_fraud_boosts_risk(self, base_txn, history_txns):
        engine = RiskEngine()
        prior = [{"outcome": "confirmed_fraud", "case_id": "CC-001"}]
        result = engine.assess(
            trigger_type="risk_score",
            bank_risk_score=0.4,
            txn=base_txn,
            customer_history=history_txns,
            identity=None,
            closed_cases=prior,
            connected_cards=[],
            shared_devices=[],
            behavioral_anomalies=[],
        )
        assert any(s.name == "prior_confirmed_fraud" and s.triggered for s in result.signals)

    def test_uncertainty_with_no_history(self, base_txn):
        engine = RiskEngine()
        result = engine.assess(
            trigger_type="risk_score",
            bank_risk_score=0.6,
            txn=base_txn,
            customer_history=[],
            identity=None,
            closed_cases=[],
            connected_cards=[],
            shared_devices=[],
            behavioral_anomalies=[],
        )
        assert len(result.uncertainty_flags) > 0


# ── PatternDetector ───────────────────────────────────────────────────────────

class TestPatternDetector:
    def test_card_testing_detected(self, base_txn):
        detector = PatternDetector()
        # 3 micro-transactions before flagged
        micro_txns = [
            {"TransactionID": f"T10{i}", "TransactionAmt": 1.0 + i,
             "channel": "online", "ts": "2016-12-05 01:30:00"}
            for i in range(3)
        ]
        result = detector.detect(
            flagged_txn=base_txn,
            card_transactions=micro_txns + [base_txn],
            identity=None,
            customer_history=[],
            shared_devices=[],
            prior_fraud_cases=[],
            trigger_type="risk_score",
        )
        assert result.pattern == FraudPattern.card_testing
        assert result.confidence > 0.6

    def test_cnp_new_device_detected(self, base_txn, history_txns):
        detector = PatternDetector()
        identity = {"id_15": "New", "id_23": "", "DeviceInfo": "iPhone", "id_30": "iOS"}
        burst = [
            {"TransactionID": f"T20{i}", "TransactionAmt": 80.0,
             "channel": "online", "ts": "2016-12-05 00:30:00"}
            for i in range(3)
        ]
        result = detector.detect(
            flagged_txn=base_txn,
            card_transactions=burst + [base_txn],
            identity=identity,
            customer_history=history_txns,
            shared_devices=[],
            prior_fraud_cases=[],
            trigger_type="risk_score",
        )
        assert result.pattern in (
            FraudPattern.card_not_present_new_device,
            FraudPattern.card_not_present_fraud,
        )

    def test_out_of_region_detected(self):
        detector = PatternDetector()
        # Customer normally in country 87
        # OOR logic: flagged in foreign region AND concurrent home activity within 24h
        history = [
            {"TransactionID": f"H{i}", "TransactionAmt": 50.0,
             "channel": "in_person", "addr2": "87", "ts": f"2016-11-0{i+1} 10:00:00"}
            for i in range(5)
        ]
        flagged = {
            "TransactionID": "T_OOR",
            "TransactionAmt": 200.0,
            "channel": "in_person",
            "addr2": "45",  # Foreign country
            "ts": "2016-12-05 12:00:00",
        }
        # Add a home-region transaction within 24h of flagged (clone indicator)
        home_concurrent = {
            "TransactionID": "H_CONCURRENT",
            "TransactionAmt": 30.0,
            "channel": "in_person",
            "addr2": "87",
            "ts": "2016-12-05 08:00:00",  # Same day, home region
        }
        full_history = history + [home_concurrent]
        result = detector.detect(
            flagged_txn=flagged,
            card_transactions=full_history + [flagged],
            identity=None,
            customer_history=full_history,
            shared_devices=[],
            prior_fraud_cases=[],
            trigger_type="risk_score",
        )
        assert result.pattern == FraudPattern.out_of_region_use

    def test_no_pattern_when_insufficient(self, base_txn, history_txns):
        detector = PatternDetector()
        result = detector.detect(
            flagged_txn=base_txn,
            card_transactions=[base_txn],
            identity=None,
            customer_history=history_txns,
            shared_devices=[],
            prior_fraud_cases=[],
            trigger_type="risk_score",
        )
        assert result.pattern == FraudPattern.none or result.confidence < 0.7


# ── ExposureEngine ────────────────────────────────────────────────────────────

class TestExposureEngine:
    def test_single_transaction_exposure(self, base_txn):
        engine = ExposureEngine()
        result = engine.calculate(
            flagged_txn=base_txn,
            related_transactions=[],
            connected_cards=[],
            shared_devices=[],
        )
        assert result.exposure_usd == pytest.approx(100.0)
        assert base_txn["TransactionID"] in result.affected_txn_ids

    def test_multiple_transaction_exposure(self, base_txn):
        engine = ExposureEngine()
        related = [
            {"TransactionID": "T002", "TransactionAmt": 50.0, "ts": "2016-12-05 00:30:00"},
            {"TransactionID": "T003", "TransactionAmt": 75.0, "ts": "2016-12-05 01:00:00"},
        ]
        result = engine.calculate(
            flagged_txn=base_txn,
            related_transactions=related,
            connected_cards=["C001-K2"],
            shared_devices=[],
        )
        assert result.exposure_usd == pytest.approx(225.0)
        assert len(result.affected_txn_ids) == 3
        assert "C001-K2" in result.connected_card_ids

    def test_connected_devices_tracked(self, base_txn):
        engine = ExposureEngine()
        result = engine.calculate(
            flagged_txn=base_txn,
            related_transactions=[],
            connected_cards=[],
            shared_devices=[{"device_key": "iPhone|iOS|safari|375x812", "cards": ["C001-K1"]}],
        )
        assert len(result.connected_device_profiles) == 1


# ── PolicyEngine ──────────────────────────────────────────────────────────────

class TestPolicyEngine:
    def setup_method(self):
        self.engine = PolicyEngine()

    def test_r1_verify_before_block_weak_signal(self):
        actions = self.engine.recommend(
            trigger_type="risk_score",
            fraud_probability=0.5,
            risk_level="MEDIUM",
            confidence=0.3,
            pattern=FraudPattern.none,
            exposure_usd=100.0,
            num_signals=1,
            num_connected_cards=0,
            num_shared_devices=0,
            has_prior_confirmed_fraud=False,
        )
        action_types = [a.action for a in actions]
        assert ActionType.VERIFY_WITH_CUSTOMER in action_types

    def test_r2_customer_denial_blocks_card(self):
        actions = self.engine.recommend(
            trigger_type="customer_report",
            fraud_probability=0.7,
            risk_level="HIGH",
            confidence=0.7,
            pattern=FraudPattern.card_not_present_fraud,
            exposure_usd=500.0,
            num_signals=3,
            num_connected_cards=0,
            num_shared_devices=0,
            has_prior_confirmed_fraud=False,
            customer_response="denied",
        )
        action_types = [a.action for a in actions]
        assert ActionType.BLOCK_CARD in action_types
        assert ActionType.CREATE_CASE in action_types

    def test_r3_confirmed_closes_case(self):
        actions = self.engine.recommend(
            trigger_type="risk_score",
            fraud_probability=0.3,
            risk_level="LOW",
            confidence=0.5,
            pattern=FraudPattern.none,
            exposure_usd=50.0,
            num_signals=1,
            num_connected_cards=0,
            num_shared_devices=0,
            has_prior_confirmed_fraud=False,
            customer_response="confirmed",
        )
        assert len(actions) == 1
        assert actions[0].action == ActionType.CLOSE_NO_FRAUD
        assert actions[0].route == ApprovalRoute.auto

    def test_r5_card_testing_decline(self):
        actions = self.engine.recommend(
            trigger_type="risk_score",
            fraud_probability=0.8,
            risk_level="HIGH",
            confidence=0.8,
            pattern=FraudPattern.card_testing,
            exposure_usd=50.0,
            num_signals=4,
            num_connected_cards=0,
            num_shared_devices=0,
            has_prior_confirmed_fraud=False,
        )
        action_types = [a.action for a in actions]
        assert ActionType.DECLINE_TRANSACTION in action_types
        assert ActionType.STEP_UP_AUTH in action_types

    def test_block_card_route_l1_under_2500(self):
        actions = self.engine.recommend(
            trigger_type="customer_report",
            fraud_probability=0.9,
            risk_level="HIGH",
            confidence=0.9,
            pattern=FraudPattern.card_not_present_fraud,
            exposure_usd=1000.0,
            num_signals=5,
            num_connected_cards=0,
            num_shared_devices=0,
            has_prior_confirmed_fraud=True,
            customer_response="denied",
        )
        for a in actions:
            if a.action == ActionType.BLOCK_CARD:
                assert a.route == ApprovalRoute.L1

    def test_block_card_route_l2_over_2500(self):
        actions = self.engine.recommend(
            trigger_type="customer_report",
            fraud_probability=0.92,
            risk_level="HIGH",
            confidence=0.9,
            pattern=FraudPattern.card_not_present_fraud,
            exposure_usd=3000.0,
            num_signals=5,
            num_connected_cards=0,
            num_shared_devices=0,
            has_prior_confirmed_fraud=True,
            customer_response="denied",
        )
        for a in actions:
            if a.action == ActionType.BLOCK_CARD:
                assert a.route == ApprovalRoute.L2

    def test_file_report_always_l2(self):
        actions = self.engine.recommend(
            trigger_type="customer_report",
            fraud_probability=0.92,
            risk_level="HIGH",
            confidence=0.9,
            pattern=FraudPattern.card_not_present_fraud,
            exposure_usd=2000.0,
            num_signals=5,
            num_connected_cards=0,
            num_shared_devices=0,
            has_prior_confirmed_fraud=True,
            customer_response="denied",
        )
        for a in actions:
            if a.action == ActionType.FILE_REPORT:
                assert a.route == ApprovalRoute.L2

    def test_r9_undocumented_escalates(self):
        actions = self.engine.recommend(
            trigger_type="analyst_request",
            fraud_probability=0.65,
            risk_level="MEDIUM",
            confidence=0.5,
            pattern=FraudPattern.undocumented,
            exposure_usd=800.0,
            num_signals=3,
            num_connected_cards=0,
            num_shared_devices=0,
            has_prior_confirmed_fraud=False,
        )
        action_types = [a.action for a in actions]
        assert ActionType.ESCALATE_TO_ANALYST in action_types

    def test_requires_sar_when_file_report_present(self):
        from app.models.case import ActionRecommendation
        actions = [
            ActionRecommendation(
                action=ActionType.FILE_REPORT,
                route=ApprovalRoute.L2,
                reason="test",
            )
        ]
        assert self.engine.requires_sar(actions) is True

    def test_no_sar_without_file_report(self):
        from app.models.case import ActionRecommendation
        actions = [
            ActionRecommendation(
                action=ActionType.BLOCK_CARD,
                route=ApprovalRoute.L1,
                reason="test",
            )
        ]
        assert self.engine.requires_sar(actions) is False
