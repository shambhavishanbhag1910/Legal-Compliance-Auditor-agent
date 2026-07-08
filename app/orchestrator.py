from uuid import uuid4

from app.agent import EvidenceAgent
from app.config import Settings
from app.consensus import build_consensus
from app.document_parser import chunk_text
from app.frameworks import FRAMEWORKS
from app.judge import evaluate_report
from app.llm import LLMClient
from app.schemas import AuditEnvelope
from app.search_index import DocumentIndex
from app.storage import Storage
from app.tools import AuditToolRegistry


class AuditOrchestrator:
    def __init__(self, settings: Settings, storage: Storage):
        self.settings = settings
        self.storage = storage

    def run(self, document_id: str, framework: str, runs: int) -> AuditEnvelope:
        source_text, _ = self.storage.load_document(document_id)
        index = DocumentIndex(chunk_text(source_text))
        registry = AuditToolRegistry(index)

        agent = EvidenceAgent(self.settings)
        evidence, traces = agent.collect(framework=framework, registry=registry)

        if not evidence:
            for rule in FRAMEWORKS[framework]:
                for result in index.search(rule["question"], top_k=2):
                    registry.seen_chunks[result["chunk_id"]] = result
            evidence = registry.evidence_bundle()

        llm = LLMClient(self.settings)
        candidates = [
            llm.structured_audit(
                document_id=document_id,
                framework=framework,
                rules=FRAMEWORKS[framework],
                evidence=evidence,
            )
            for _ in range(runs)
        ]

        report, agreement = build_consensus(candidates)
        judge = evaluate_report(llm, source_text=source_text, report=report)

        envelope = AuditEnvelope(
            audit_id=str(uuid4()),
            report=report,
            consensus_agreement=agreement,
            candidate_count=len(candidates),
            judge=judge,
            tool_trace=traces,
        )

        self.storage.save_audit(
            envelope.audit_id,
            envelope.model_dump(mode="json"),
        )
        return envelope
