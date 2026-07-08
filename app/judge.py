from app.frameworks import FRAMEWORKS
from app.llm import LLMClient
from app.schemas import AuditReport, JudgeResult


def evaluate_report(llm: LLMClient, *, source_text: str, report: AuditReport) -> JudgeResult:
    return llm.judge(
        source_text=source_text,
        report=report,
        rules=FRAMEWORKS[report.framework],
    )
