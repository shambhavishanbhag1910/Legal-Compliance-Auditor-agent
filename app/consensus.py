from collections import Counter, defaultdict


from app.schemas import AuditReport, RiskLevel

def majority_value(values: list[str]) -> str:
    if not values:
        raise ValueError("values cannot be empty")
    return Counter(values).most_common(1)[0][0]


def build_consensus(reports: list[AuditReport]) -> tuple[AuditReport, float]:
    if len(reports) < 3:
        raise ValueError("Self-consistency requires at least 3 reports.")

    grouped = defaultdict(list)
    for report in reports:
        for finding in report.findings:
            grouped[finding.rule_id].append(finding)

    final_findings = []
    agreements = []

    for rule_id in sorted(grouped):
        candidates = grouped[rule_id]
        statuses = [c.status.value for c in candidates]
        winning_status = majority_value(statuses)
        agreements.append(statuses.count(winning_status) / len(statuses))
        matching = [c for c in candidates if c.status.value == winning_status]
        chosen = max(matching, key=lambda c: (len(c.evidence), len(c.summary), len(c.remediation)))
        final_findings.append(chosen)

    risk = RiskLevel(majority_value([r.overall_risk.value for r in reports]))
    representative = max(reports, key=lambda r: len(r.executive_summary))

    final_report = AuditReport(
        document_id=representative.document_id,
        framework=representative.framework,
        executive_summary=representative.executive_summary,
        overall_risk=risk,
        findings=final_findings,
        limitations=representative.limitations,
    )
    agreement = sum(agreements) / len(agreements) if agreements else 0.0
    return final_report, round(agreement, 4)
