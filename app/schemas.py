from enum import Enum
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

class StrictBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )


class ComplianceStatus(str, Enum):
    compliant = "compliant"
    non_compliant = "non_compliant"
    unclear = "unclear"
    not_applicable = "not_applicable"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class EvidenceQuote(StrictBaseModel):
    quote: str = Field(
        description=(
            "Short verbatim quote from "
            "the source document."
        )
    )

    chunk_id: str = Field(
        description=(
            "Chunk ID where the quote was found."
        )
    )


class ComplianceFinding(StrictBaseModel):
    rule_id: str

    rule_name: str

    status: ComplianceStatus

    severity: Severity

    summary: str

    evidence: list[EvidenceQuote]

    remediation: str


class AuditReport(StrictBaseModel):
    document_id: str

    framework: Literal[
        "privacy",
        "tos",
        "financial",
    ]

    executive_summary: str

    overall_risk: RiskLevel

    findings: list[ComplianceFinding]

    limitations: list[str]


class JudgeResult(StrictBaseModel):
    faithfulness: float = Field(
        ge=0.0,
        le=1.0,
    )

    completeness: float = Field(
        ge=0.0,
        le=1.0,
    )

    hallucination_rate: float = Field(
        ge=0.0,
        le=1.0,
    )

    unsupported_finding_ids: list[str]

    fabricated_claims: list[str]

    comments: str


class AuditRequest(BaseModel):
    document_id: str
    framework: Literal["privacy", "tos", "financial"]
    runs: int = Field(default=3, ge=3, le=5)


class ToolTrace(BaseModel):
    tool_name: str
    purpose: str
    arguments: dict
    result_preview: str


class AuditEnvelope(BaseModel):
    audit_id: str
    report: AuditReport
    consensus_agreement: float = Field(ge=0.0, le=1.0)
    candidate_count: int
    judge: JudgeResult
    tool_trace: list[ToolTrace]


class DocumentCreated(BaseModel):
    document_id: str
    filename: str
    characters: int
