import time
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
    def __init__(
        self,
        settings: Settings,
        storage: Storage,
    ):
        self.settings = settings
        self.storage = storage


    def run(
        self,
        document_id: str,
        framework: str,
        runs: int,
    ) -> AuditEnvelope:

        # ---------------------------------------------------------
        # 1. Load source document
        # ---------------------------------------------------------

        source_text, _ = self.storage.load_document(
            document_id
        )


        # ---------------------------------------------------------
        # 2. Validate framework
        # ---------------------------------------------------------

        if framework not in FRAMEWORKS:
            raise ValueError(
                f"Unknown framework: {framework}"
            )


        # ---------------------------------------------------------
        # 3. Chunk and build local BM25 index
        # ---------------------------------------------------------

        chunks = chunk_text(
            source_text
        )

        index = DocumentIndex(
            chunks
        )

        registry = AuditToolRegistry(
            index
        )


        # ---------------------------------------------------------
        # 4. Deterministic baseline retrieval
        #
        # Every rule gets local BM25 retrieval coverage.
        # This does not call the LLM.
        # ---------------------------------------------------------

        print(
            "[Baseline Retrieval] "
            "Collecting evidence for all framework rules..."
        )

        for rule in FRAMEWORKS[framework]:

            results = index.search(
                rule["question"],
                top_k=2,
            )

            for result in results:

                registry.seen_chunks[
                    result["chunk_id"]
                ] = result


        print(
            "[Baseline Retrieval] "
            f"Collected {len(registry.seen_chunks)} "
            "unique chunks."
        )


        # ---------------------------------------------------------
        # 5. Agent follow-up exploration
        # ---------------------------------------------------------

        agent = EvidenceAgent(
            self.settings
        )

        _, traces = agent.collect(
            framework=framework,
            registry=registry,
        )


        # ---------------------------------------------------------
        # 6. Unified evidence bundle
        # ---------------------------------------------------------

        evidence = (
            registry.evidence_bundle()
        )

        if not evidence:
            raise RuntimeError(
                "No evidence chunks were collected."
            )


        print(
            f"[Evidence Bundle] "
            f"{len(evidence)} unique chunks ready."
        )


        # ---------------------------------------------------------
        # 7. Create LLM client
        #
        # IMPORTANT:
        # llm must be created BEFORE candidate generation.
        # ---------------------------------------------------------

        llm = LLMClient(
            self.settings
        )


        # ---------------------------------------------------------
        # 8. Generate self-consistency candidates
        # ---------------------------------------------------------

        candidates = []

        for candidate_number in range(
            1,
            runs + 1,
        ):

            print(
                f"[Candidate Generation] "
                f"{candidate_number}/{runs}"
            )

            candidate = llm.structured_audit(
                document_id=document_id,
                framework=framework,
                rules=FRAMEWORKS[framework],
                evidence=evidence,
            )

            candidates.append(
                candidate
            )


            # Allow some space between candidate calls
            # to reduce burst pressure on the model API.

            if candidate_number < runs:

                delay = 12

                print(
                    f"[Candidate Generation] "
                    f"Waiting {delay} seconds "
                    "before next candidate..."
                )

                time.sleep(
                    delay
                )


        # ---------------------------------------------------------
        # 9. Consensus
        # ---------------------------------------------------------

        print(
            "[Consensus] "
            "Building rule-level majority consensus..."
        )

        report, agreement = build_consensus(
            candidates
        )


        # ---------------------------------------------------------
        # 10. Independent judge evaluation
        # ---------------------------------------------------------

        print(
            "[Judge] "
            "Evaluating final consensus report..."
        )

        judge = evaluate_report(
            llm,
            source_text=source_text,
            report=report,
        )


        # ---------------------------------------------------------
        # 11. Build final envelope
        # ---------------------------------------------------------

        envelope = AuditEnvelope(
            audit_id=str(
                uuid4()
            ),
            report=report,
            consensus_agreement=agreement,
            candidate_count=len(
                candidates
            ),
            judge=judge,
            tool_trace=traces,
        )


        # ---------------------------------------------------------
        # 12. Save audit
        # ---------------------------------------------------------

        self.storage.save_audit(
            envelope.audit_id,
            envelope.model_dump(
                mode="json"
            ),
        )


        print(
            f"[Audit Complete] "
            f"Audit ID: {envelope.audit_id}"
        )


        return envelope