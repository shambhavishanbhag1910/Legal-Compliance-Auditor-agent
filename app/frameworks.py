FRAMEWORKS: dict[str, list[dict[str, str]]] = {
    "privacy": [
        {"rule_id": "PRIV-001", "rule_name": "Data collection disclosure", "question": "Does the policy clearly disclose the categories of personal data collected?"},
        {"rule_id": "PRIV-002", "rule_name": "Purpose of processing", "question": "Does the policy explain why collected personal data is used?"},
        {"rule_id": "PRIV-003", "rule_name": "Data sharing disclosure", "question": "Does the policy explain whether and with whom personal data is shared?"},
        {"rule_id": "PRIV-004", "rule_name": "Retention", "question": "Does the policy describe retention periods or objective retention criteria?"},
        {"rule_id": "PRIV-005", "rule_name": "User rights", "question": "Does the policy explain user privacy rights and how to exercise them?"},
        {"rule_id": "PRIV-006", "rule_name": "Security safeguards", "question": "Does the policy describe reasonable safeguards or security practices?"},
        {"rule_id": "PRIV-007", "rule_name": "Privacy contact channel", "question": "Does the policy provide a way to contact the organization about privacy matters?"},
    ],
    "tos": [
        {"rule_id": "TOS-001", "rule_name": "Account responsibilities", "question": "Are user account responsibilities stated?"},
        {"rule_id": "TOS-002", "rule_name": "Acceptable use", "question": "Are prohibited or acceptable uses described?"},
        {"rule_id": "TOS-003", "rule_name": "Payment and refund terms", "question": "Are payment, billing, and refund terms explained where applicable?"},
        {"rule_id": "TOS-004", "rule_name": "Termination and suspension", "question": "Are termination or suspension conditions explained?"},
        {"rule_id": "TOS-005", "rule_name": "Warranty and liability", "question": "Are warranty disclaimers and liability limitations described?"},
        {"rule_id": "TOS-006", "rule_name": "Governing law and disputes", "question": "Are governing law or dispute resolution terms described?"},
    ],
    "financial": [
        {"rule_id": "FIN-001", "rule_name": "Reporting period", "question": "Is the reporting period clearly identified?"},
        {"rule_id": "FIN-002", "rule_name": "Revenue disclosure", "question": "Is revenue or an equivalent top-line measure disclosed?"},
        {"rule_id": "FIN-003", "rule_name": "Material risks", "question": "Are material financial or operating risks disclosed?"},
        {"rule_id": "FIN-004", "rule_name": "Accounting basis", "question": "Is the accounting basis or applicable reporting standard identified?"},
        {"rule_id": "FIN-005", "rule_name": "Forward-looking uncertainty", "question": "Are significant assumptions, uncertainties, or forward-looking caveats identified?"},
    ],
}

DEFINITIONS = {
    "personal data": "Information relating to an identified or identifiable natural person.",
    "retention": "The period for which data is kept, or the criteria used to determine that period.",
    "data subject rights": "Rights individuals may have over personal data, such as access, correction, deletion, restriction, or objection.",
    "material risk": "A risk significant enough that a reasonable stakeholder could consider it important to a decision.",
    "limitation of liability": "A contractual provision that limits the scope or amount of liability one party may owe.",
}
