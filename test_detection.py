"""Focused tests for local deterministic pattern detection."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from agent.detection import detect_case


ROOT = Path(__file__).parent


class DetectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profiles = json.loads((ROOT / "artifacts/case_profiles.json").read_text(encoding="utf-8"))
        cls.shared = json.loads((ROOT / "artifacts/shared_entities.json").read_text(encoding="utf-8"))

    def test_hhg_014_detects_shared_device_and_undocumented_coordination(self):
        profile = next(item for item in self.profiles if item["case_id"] == "HHG-014")
        result = detect_case(profile, self.shared)
        matches = {item["pattern"]: item for item in result["detectors"] if item["matched"]}
        self.assertIn("shared_entity", matches)
        self.assertIn("undocumented", matches)
        self.assertGreaterEqual(len(matches["shared_entity"]["connected_card_ids"]), 7)
        self.assertIn("3478561", matches["shared_entity"]["transaction_ids"])

    def test_single_online_transaction_is_not_cnp_burst(self):
        profile = next(item for item in self.profiles if item["case_id"] == "HHG-002")
        result = detect_case(profile, self.shared)
        cnp = next(item for item in result["detectors"] if item["pattern"] == "cnp")
        self.assertFalse(cnp["matched"])

    def test_new_device_detector_uses_identity_record(self):
        profile = next(item for item in self.profiles if item["case_id"] == "HHG-014")
        result = detect_case(profile, self.shared)
        new_device = next(item for item in result["detectors"] if item["pattern"] == "cnp_new_device")
        self.assertTrue(new_device["matched"])
        self.assertEqual(new_device["transaction_ids"], ["3478561"])

    def test_two_customer_overlap_is_shared_entity_but_not_undocumented_ring(self):
        profile = next(item for item in self.profiles if item["case_id"] == "HHG-017")
        shared = dict(self.shared)
        shared["HHG-017"] = {
            "shared_devices": {
                "device": [
                    {"transaction_id": "t1", "customer_id": "C1", "card_id": "C1-K1"},
                    {"transaction_id": "t2", "customer_id": "C2", "card_id": "C2-K1"},
                ],
            },
            "connected_customer_ids": ["C1", "C2"],
            "connected_card_ids": ["C1-K1", "C2-K1"],
        }
        result = detect_case(profile, shared)
        undocumented = next(item for item in result["detectors"] if item["pattern"] == "undocumented")
        self.assertFalse(undocumented["matched"])


if __name__ == "__main__":
    unittest.main()