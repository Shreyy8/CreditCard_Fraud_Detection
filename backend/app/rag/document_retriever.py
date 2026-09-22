"""
Document retriever — fraud policy, typology, and regulatory guidance.

Encodes the known policy rules, fraud typology descriptions, and
FinCEN/regulatory guidance from the README as structured retrieval records.

NO external documents or hallucinated content.
Everything here is sourced directly from the README / policy section.
"""

from __future__ import annotations

from typing import Any

# ── Policy rules (Fraud Policy v1.0 from README) ─────────────────────────────

POLICY_RULES: dict[str, dict[str, Any]] = {
    "R1": {
        "rule_id": "R1",
        "title": "Verify before you block on a weak signal",
        "text": (
            "If the case rests on a single signal (including risk score alone) "
            "and assessed fraud probability is below 0.70, recommend "
            "VERIFY_WITH_CUSTOMER or STEP_UP_AUTH before any block. "
            "Blocking a legitimate customer on one signal is a policy breach."
        ),
        "triggers": ["single_signal", "risk_score_only", "low_probability"],
        "actions": ["VERIFY_WITH_CUSTOMER", "STEP_UP_AUTH"],
        "fraud_types": ["all"],
    },
    "R2": {
        "rule_id": "R2",
        "title": "Customer denies the transaction",
        "text": (
            "Recommend BLOCK_CARD and CREATE_CASE. Add FILE_REPORT if "
            "exposure exceeds $1,000 or the case connects to a shared "
            "device profile or another card's fraud."
        ),
        "triggers": ["customer_report", "customer_denial"],
        "actions": ["BLOCK_CARD", "CREATE_CASE", "FILE_REPORT"],
        "fraud_types": ["all"],
    },
    "R3": {
        "rule_id": "R3",
        "title": "Customer confirms the transaction",
        "text": (
            "Recommend CLOSE_NO_FRAUD. Note the confirmation in the case file."
        ),
        "triggers": ["customer_confirmation"],
        "actions": ["CLOSE_NO_FRAUD"],
        "fraud_types": ["all"],
    },
    "R4": {
        "rule_id": "R4",
        "title": "No reply within 24 hours",
        "text": (
            "Recommend MONITOR_CARD and DECLINE_TRANSACTION for pending "
            "authorizations. Escalate if exposure exceeds $500."
        ),
        "triggers": ["no_customer_reply"],
        "actions": ["MONITOR_CARD", "DECLINE_TRANSACTION", "ESCALATE_TO_ANALYST"],
        "fraud_types": ["all"],
    },
    "R5": {
        "rule_id": "R5",
        "title": "Card testing pattern",
        "text": (
            "Three or more small online authorizations on one card within an hour, "
            "followed by a larger purchase: recommend DECLINE_TRANSACTION and "
            "STEP_UP_AUTH. If a purchase over $100 has already cleared, "
            "recommend BLOCK_CARD."
        ),
        "triggers": ["card_testing", "small_auth_burst"],
        "actions": ["DECLINE_TRANSACTION", "STEP_UP_AUTH", "BLOCK_CARD"],
        "fraud_types": ["card_testing"],
    },
    "R6": {
        "rule_id": "R6",
        "title": "Shared origin across cards",
        "text": (
            "When several cards show fraud from the same device profile, billing "
            "region, or recipient email in one window, name the shared element, "
            "recommend CREATE_CASE and FILE_REPORT, and MONITOR_CONNECTED_CARDS "
            "for every card that shares it."
        ),
        "triggers": ["shared_device", "shared_region", "multi_card"],
        "actions": ["CREATE_CASE", "FILE_REPORT", "MONITOR_CONNECTED_CARDS"],
        "fraud_types": ["all"],
    },
    "R7": {
        "rule_id": "R7",
        "title": "Disputed but legitimate (recurring charge)",
        "text": (
            "When the customer disputes a charge that matches their own recurring "
            "pattern (same merchant, same amount, monthly), recommend CREATE_CASE, "
            "VERIFY_WITH_CUSTOMER, and WARN_CUSTOMER. Do not block."
        ),
        "triggers": ["recurring_dispute", "customer_report"],
        "actions": ["CREATE_CASE", "VERIFY_WITH_CUSTOMER", "WARN_CUSTOMER"],
        "fraud_types": ["none"],
    },
    "R8": {
        "rule_id": "R8",
        "title": "Escalate when uncertain and exposed",
        "text": (
            "If the verdict is uncertain and exposure exceeds $500, or the "
            "evidence conflicts, recommend ESCALATE_TO_ANALYST."
        ),
        "triggers": ["uncertain_verdict", "conflicting_evidence", "high_exposure"],
        "actions": ["ESCALATE_TO_ANALYST"],
        "fraud_types": ["all"],
    },
    "R9": {
        "rule_id": "R9",
        "title": "Undocumented patterns",
        "text": (
            "When activity fits none of the known patterns but the evidence shows "
            "coordinated or repeated abuse across customers, recommend CREATE_CASE, "
            "FILE_REPORT, and ESCALATE_TO_ANALYST, and describe the pattern."
        ),
        "triggers": ["undocumented_pattern", "coordinated_abuse"],
        "actions": ["CREATE_CASE", "FILE_REPORT", "ESCALATE_TO_ANALYST"],
        "fraud_types": ["undocumented"],
    },
    "R10": {
        "rule_id": "R10",
        "title": "BLOCK_ALL_CARDS threshold",
        "text": (
            "Never BLOCK_ALL_CARDS unless at least two of the customer's cards "
            "show confirmed fraud or the customer's credentials are confirmed compromised."
        ),
        "triggers": ["multi_card_fraud", "credential_compromise"],
        "actions": ["BLOCK_ALL_CARDS"],
        "fraud_types": ["account_takeover"],
    },
}

# ── SAR filing policy ─────────────────────────────────────────────────────────

SAR_POLICY = {
    "doc_id": "SAR_POLICY",
    "title": "Suspicious Activity Report filing criteria",
    "source": "Fraud Policy v1.0 section 3a",
    "text": (
        "File a SAR (FILE_REPORT) when fraud is confirmed or strongly suspected "
        "AND at least one of: exposure > $1,000; activity connects to shared "
        "device profile, shared region cluster, or another customer's fraud; "
        "pattern is coordinated or undocumented (rule R9). "
        "A SAR always has a case behind it. Most cases never need a report. "
        "The report narrative must stand on its own: who, what, when, where, "
        "how, and why it is suspicious."
    ),
}

# ── Fraud typologies (from README) ────────────────────────────────────────────

FRAUD_TYPOLOGIES: dict[str, dict[str, Any]] = {
    "card_testing": {
        "typology_id": "card_testing",
        "name": "Card Testing",
        "description": (
            "A stolen card number is verified before use: three or more tiny "
            "online authorizations (often under $5) within an hour, then a larger "
            "purchase. Confirmed by the sequence itself. Policy R5."
        ),
        "indicators": [
            "3+ online authorizations < $5 within 1 hour",
            "followed by larger purchase",
            "no physical card present",
        ],
        "policy_rules": ["R5"],
    },
    "card_not_present_fraud": {
        "typology_id": "card_not_present_fraud",
        "name": "Card-Not-Present Fraud",
        "description": (
            "The card number is used online without the physical card. Amounts "
            "and products inconsistent with cardholder history, often in a burst "
            "of 2-4 transactions within 48 hours. One unusual online purchase is "
            "ambiguous — verify first. Policy R1-R4."
        ),
        "indicators": [
            "online channel transaction",
            "amounts inconsistent with history",
            "burst of 2-4 transactions within 48h",
            "unfamiliar merchant/product",
        ],
        "policy_rules": ["R1", "R2", "R3", "R4"],
    },
    "card_not_present_new_device": {
        "typology_id": "card_not_present_new_device",
        "name": "CNP from New Device",
        "description": (
            "Same as CNP fraud, but the identity record marks the device as 'New' "
            "for this account, sometimes behind a proxy. Stronger signal than "
            "plain CNP, but still not proof — people buy new phones. Policy R1-R4."
        ),
        "indicators": [
            "id_15=New (new device)",
            "online transaction",
            "proxy connection (id_23=anonymous/hidden)",
            "amounts inconsistent with history",
        ],
        "policy_rules": ["R1", "R2", "R3", "R4"],
    },
    "out_of_region_use": {
        "typology_id": "out_of_region_use",
        "name": "Out-of-Region Use",
        "description": (
            "Card-present purchases in a billing region the cardholder has no "
            "history in, while normal activity continues at home. Several days "
            "of purchases in one new region is a trip, not a clone. Policy R2, R3."
        ),
        "indicators": [
            "in-person channel",
            "addr2 not in customer's historical regions",
            "concurrent home-region activity (clone indicator)",
        ],
        "policy_rules": ["R2", "R3"],
    },
    "account_takeover": {
        "typology_id": "account_takeover",
        "name": "Account Takeover",
        "description": (
            "Mixed-channel activity inconsistent with the cardholder, often with "
            "device and match-flag anomalies (M columns = F), pointing to stolen "
            "credentials rather than a stolen card number. Policy R2."
        ),
        "indicators": [
            "M-flag mismatches (M1-M9 = F)",
            "id_34 match_status anomaly",
            "id_15=New (new device)",
            "mixed online/in-person channels",
            "customer dispute",
        ],
        "policy_rules": ["R2", "R8"],
    },
    "undocumented": {
        "typology_id": "undocumented",
        "name": "Undocumented Pattern",
        "description": (
            "Activity fitting none of the five known patterns but showing "
            "coordinated or repeated suspicious behavior across accounts. "
            "Describe in your own words; do not force into a known category. "
            "Policy R9."
        ),
        "indicators": [
            "shared device across multiple cards",
            "coordinated timing",
            "multiple customers affected",
            "does not fit R1-R10 cleanly",
        ],
        "policy_rules": ["R9"],
    },
}

# ── Regulatory references (from README) ──────────────────────────────────────

REGULATORY_REFS = [
    {
        "ref_id": "FINCEN_SAR_NARRATIVE",
        "source": "FinCEN SAR Narrative Guidance",
        "key_points": [
            "SAR narrative must cover: who, what, when, where, how, why suspicious",
            "Must stand on its own without reference to other documents",
            "Six to twelve sentences minimum for complex activity",
        ],
    },
    {
        "ref_id": "FINCEN_ACCOUNT_TAKEOVER",
        "source": "FinCEN Advisory FIN-2011-A016",
        "key_points": [
            "Account takeover: unauthorized access to online banking credentials",
            "Red flags: new device, unusual IP, sudden high-value transfers",
            "File SAR within 30 days of initial detection",
        ],
    },
    {
        "ref_id": "FFIEC_RED_FLAGS",
        "source": "FFIEC BSA/AML Manual — Red Flags",
        "key_points": [
            "Multiple cards showing activity from same device = network indicator",
            "Unusual velocity of transactions in short window",
            "Transactions inconsistent with established customer profile",
        ],
    },
]


class DocumentRetriever:
    """
    Retrieves policy, typology, and regulatory knowledge relevant to an investigation.

    Returns only records with provenance — every item names its source.
    No hallucinated content.
    """

    def get_policy_rules(
        self,
        trigger_type: str,
        pattern: str,
        fraud_probability: float,
        has_shared_device: bool,
        exposure_usd: float,
        num_signals: int,
    ) -> list[dict[str, Any]]:
        """
        Return policy rules applicable to this investigation.
        Only rules whose conditions match the current evidence state.
        """
        applicable: list[dict[str, Any]] = []

        # R1 — weak single signal
        if fraud_probability < 0.70 and num_signals <= 1:
            applicable.append(POLICY_RULES["R1"])

        # R2 — customer denied
        if trigger_type == "customer_report":
            applicable.append(POLICY_RULES["R2"])

        # R3 — confirmation (always include for context)
        applicable.append(POLICY_RULES["R3"])

        # R4 — no reply
        applicable.append(POLICY_RULES["R4"])

        # R5 — card testing
        if pattern == "card_testing":
            applicable.append(POLICY_RULES["R5"])

        # R6 — shared origin
        if has_shared_device:
            applicable.append(POLICY_RULES["R6"])

        # R7 — legitimate dispute
        if trigger_type == "customer_report":
            applicable.append(POLICY_RULES["R7"])

        # R8 — uncertain + exposed
        if exposure_usd > 500 and (fraud_probability < 0.70 or num_signals < 2):
            applicable.append(POLICY_RULES["R8"])

        # R9 — undocumented
        if pattern == "undocumented":
            applicable.append(POLICY_RULES["R9"])

        # R10 — block all (always include for safety)
        applicable.append(POLICY_RULES["R10"])

        # Add SAR policy if exposure is high
        if exposure_usd > 1000 or has_shared_device:
            applicable.append(SAR_POLICY)

        # Deduplicate
        seen: set[str] = set()
        unique: list[dict] = []
        for r in applicable:
            rid = r.get("rule_id") or r.get("doc_id") or r.get("title", "")
            if rid not in seen:
                seen.add(rid)
                unique.append(r)

        return unique

    def get_typology(self, pattern: str) -> list[dict[str, Any]]:
        """Return typology docs for the detected pattern + related ones."""
        results = []
        if pattern in FRAUD_TYPOLOGIES:
            results.append(FRAUD_TYPOLOGIES[pattern])
        # Always add undocumented as a reference option
        if pattern != "undocumented" and "undocumented" in FRAUD_TYPOLOGIES:
            results.append(FRAUD_TYPOLOGIES["undocumented"])
        return results

    def get_regulatory_refs(
        self, pattern: str, trigger_type: str
    ) -> list[dict[str, Any]]:
        """Return regulatory references relevant to this investigation type."""
        refs = []
        if trigger_type == "customer_report" or pattern in (
            "account_takeover", "card_not_present_fraud", "card_not_present_new_device"
        ):
            refs.append(REGULATORY_REFS[0])   # SAR narrative
        if pattern == "account_takeover":
            refs.append(REGULATORY_REFS[1])   # ATO advisory
        refs.append(REGULATORY_REFS[2])        # FFIEC red flags always
        return refs
