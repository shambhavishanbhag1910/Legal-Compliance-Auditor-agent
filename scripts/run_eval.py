import json
from pathlib import Path

from app.config import get_settings
from app.document_parser import parse_document
from app.metrics import precision_recall_f1
from app.orchestrator import AuditOrchestrator
from app.storage import build_storage
import time

def main() -> None:
    settings = get_settings()
    storage = build_storage(settings)
    orchestrator = AuditOrchestrator(settings, storage)

    cases = json.loads(Path("eval/golden_cases.json").read_text(encoding="utf-8"))
    totals = {"tp": 0, "fp": 0, "fn": 0}

    for case in cases:
        doc_path = Path(case["document_path"])
        text = parse_document(doc_path.name, doc_path.read_bytes())
        storage.save_document(
            case["document_id"],
            text,
            {
                "document_id": case["document_id"],
                "filename": doc_path.name,
                "characters": len(text),
            },
        )

        envelope = orchestrator.run(
            document_id=case["document_id"],
            framework=case["framework"],
            runs=3,
        )

        predicted = {
            finding.rule_id
            for finding in envelope.report.findings
            if finding.status.value == "non_compliant"
        }
        expected = set(case["non_compliant_rule_ids"])
        score = precision_recall_f1(predicted, expected)

        totals["tp"] += score.tp
        totals["fp"] += score.fp
        totals["fn"] += score.fn

        print(json.dumps({
            "case_id": case["case_id"],
            "predicted": sorted(predicted),
            "expected": sorted(expected),
            "precision": score.precision,
            "recall": score.recall,
            "f1": score.f1,
            "faithfulness": envelope.judge.faithfulness,
            "hallucination_rate": envelope.judge.hallucination_rate,
        }, indent=2))

    micro_precision = totals["tp"] / (totals["tp"] + totals["fp"]) if totals["tp"] + totals["fp"] else 0
    micro_recall = totals["tp"] / (totals["tp"] + totals["fn"]) if totals["tp"] + totals["fn"] else 0
    micro_f1 = (
        2 * micro_precision * micro_recall / (micro_precision + micro_recall)
        if micro_precision + micro_recall else 0
    )

    print("\nMICRO AVERAGE")
    print(json.dumps({
        "precision": round(micro_precision, 4),
        "recall": round(micro_recall, 4),
        "f1": round(micro_f1, 4),
        **totals,
    }, indent=2)
    )
    time.sleep(2)


if __name__ == "__main__":
    main()
