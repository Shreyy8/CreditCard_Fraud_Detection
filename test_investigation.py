"""Contract tests for local answer composition and validation."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from agent.investigation.calibration import fit_isotonic
from agent.investigation.composer import compose_answer
from agent.investigation.validator import build_dataset_index, validate_answer


ROOT = Path(__file__).parent


class InvestigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profiles = json.loads((ROOT / "artifacts/case_profiles.json").read_text(encoding="utf-8"))
        cls.patterns = json.loads((ROOT / "artifacts/pattern_matches.json").read_text(encoding="utf-8"))
        cls.index = build_dataset_index(ROOT / "DataSet", ROOT / "artifacts/transaction_cards.csv")

    def test_hhg_014_composes_a_valid_answer(self):
        profile = next(item for item in self.profiles if item["case_id"] == "HHG-014")
        pattern = next(item for item in self.patterns if item["case_id"] == "HHG-014")
        answer = compose_answer(profile, pattern)
        self.assertEqual(validate_answer(answer, self.index), [])
        self.assertTrue(answer["sar"]["file"])
        self.assertEqual(answer["case"]["pattern"], "undocumented")

    def test_validator_rejects_sar_action_mismatch(self):
        profile = next(item for item in self.profiles if item["case_id"] == "HHG-002")
        pattern = next(item for item in self.patterns if item["case_id"] == "HHG-002")
        answer = compose_answer(profile, pattern)
        answer["sar"]["file"] = True
        errors = validate_answer(answer, self.index)
        self.assertTrue(any("sar.file" in error for error in errors))

    def test_validator_rejects_unknown_transaction(self):
        profile = next(item for item in self.profiles if item["case_id"] == "HHG-002")
        pattern = next(item for item in self.patterns if item["case_id"] == "HHG-002")
        answer = compose_answer(profile, pattern)
        answer["case"]["affected_txn_ids"] = ["not-a-real-transaction"]
        errors = validate_answer(answer, self.index)
        self.assertTrue(any("unknown id" in error for error in errors))

    def test_customer_report_records_denial_and_changes_actions(self):
        profile = next(item for item in self.profiles if item["case_id"] == "HHG-003")
        pattern = next(item for item in self.patterns if item["case_id"] == "HHG-003")
        answer = compose_answer(profile, pattern)
        self.assertEqual(answer["evidence_requests"][0]["type"], "customer_validation")
        self.assertNotEqual(answer["next_best_actions"]["initial"], answer["next_best_actions"]["final"])
        self.assertTrue(any(item["action"] == "BLOCK_CARD" for item in answer["next_best_actions"]["final"]))
        self.assertEqual(validate_answer(answer, self.index), [])

    def test_isotonic_calibrator_is_monotonic(self):
        calibrator = fit_isotonic([0.1, 0.2, 0.3, 0.4], [1, 0, 1, 1])
        values = [calibrator.predict(value) for value in (0.0, 0.1, 0.2, 0.3, 0.4, 1.0)]
        self.assertEqual(values, sorted(values))


if __name__ == "__main__":
    unittest.main()