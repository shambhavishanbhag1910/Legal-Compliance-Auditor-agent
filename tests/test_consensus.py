from app.consensus import build_consensus
from app.schemas import (
    AuditReport,
    ComplianceFinding,
    ComplianceStatus,
    RiskLevel,
    Severity,
)


def make_report(status: ComplianceStatus, risk: RiskLevel) -> AuditReport:
    return AuditReport(
        document_id="doc",
        framework="privacy",
        executive_summary="Summary",
        overall_risk=risk,
        findings=[
            ComplianceFinding(
                rule_id="PRIV-001",
                rule_name="Test",
                status=status,
                severity=Severity.medium,
                summary="Finding",
                evidence=[],
                remediation="Review.",
            )
        ],
        limitations=[],
    )


def test_consensus_uses_majority_status():
    reports = [
        make_report(ComplianceStatus.compliant, RiskLevel.low),
        make_report(ComplianceStatus.non_compliant, RiskLevel.high),
        make_report(ComplianceStatus.non_compliant, RiskLevel.high),
    ]
    report, agreement = build_consensus(reports)
    assert report.findings[0].status == ComplianceStatus.non_compliant
    assert report.overall_risk == RiskLevel.high
    assert agreement == 0.6667
