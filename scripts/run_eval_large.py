from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.document_parser import parse_document
from app.metrics import precision_recall_f1
from app.orchestrator import AuditOrchestrator
from app.storage import build_storage


DEFAULT_CASES = Path("eval/golden_cases_30.json")
RESULT_DIR = Path("eval_results")
CASE_RESULT_FILE = RESULT_DIR / "case_results.jsonl"
SUMMARY_FILE = RESULT_DIR / "latest_summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate the compliance auditor on the 30-case benchmark."
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES,
        help="Path to case JSON file.",
    )
    parser.add_argument(
        "--framework",
        choices=["privacy", "tos", "financial"],
        help="Run only one framework.",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Start index after framework filtering.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of cases to run.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        choices=[3, 4, 5],
        help="Self-consistency candidate count.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=3.0,
        help="Seconds to wait between cases.",
    )
    parser.add_argument(
        "--fresh-results",
        action="store_true",
        help="Delete prior JSONL results before this run.",
    )
    return parser.parse_args()


def safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def load_cases(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def select_cases(
    cases: list[dict[str, Any]],
    *,
    framework: str | None,
    start: int,
    limit: int | None,
) -> list[dict[str, Any]]:
    selected = [
        case
        for case in cases
        if framework is None or case["framework"] == framework
    ]
    selected = selected[start:]
    if limit is not None:
        selected = selected[:limit]
    return selected


def append_case_result(result: dict[str, Any]) -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    with CASE_RESULT_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result, ensure_ascii=False) + "\n")

def load_all_results() -> list[dict[str, Any]]:
    """
    Load all accumulated evaluation results from JSONL.

    If the same case was run more than once,
    keep only the latest result for that case_id.
    """

    if not CASE_RESULT_FILE.exists():
        return []

    results_by_case: dict[str, dict[str, Any]] = {}

    with CASE_RESULT_FILE.open(
        "r",
        encoding="utf-8",
    ) as handle:

        for line in handle:
            line = line.strip()

            if not line:
                continue

            result = json.loads(line)

            results_by_case[
                result["case_id"]
            ] = result

    return list(
        results_by_case.values()
    )

def build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {"tp": 0, "fp": 0, "fn": 0}
    framework_totals: dict[str, dict[str, int]] = defaultdict(
        lambda: {"tp": 0, "fp": 0, "fn": 0}
    )

    for result in results:
        for key in totals:
            totals[key] += result[key]
            framework_totals[result["framework"]][key] += result[key]

    precision = safe_divide(totals["tp"], totals["tp"] + totals["fp"])
    recall = safe_divide(totals["tp"], totals["tp"] + totals["fn"])
    f1 = safe_divide(2 * precision * recall, precision + recall)

    framework_summary = {}
    for framework, counts in framework_totals.items():
        p = safe_divide(counts["tp"], counts["tp"] + counts["fp"])
        r = safe_divide(counts["tp"], counts["tp"] + counts["fn"])
        framework_summary[framework] = {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(safe_divide(2 * p * r, p + r), 4),
            **counts,
        }

    count = len(results)
    return {
        "cases_completed": count,
        "micro_precision": round(precision, 4),
        "micro_recall": round(recall, 4),
        "micro_f1": round(f1, 4),
        "avg_faithfulness": round(
            sum(r["faithfulness"] for r in results) / count, 4
        ) if count else 0.0,
        "avg_completeness": round(
            sum(r["completeness"] for r in results) / count, 4
        ) if count else 0.0,
        "avg_hallucination_rate": round(
            sum(r["hallucination_rate"] for r in results) / count, 4
        ) if count else 0.0,
        "avg_consensus_agreement": round(
            sum(r["consensus_agreement"] for r in results) / count, 4
        ) if count else 0.0,
        "frameworks": framework_summary,
        **totals,
    }


def main() -> None:
    args = parse_args()

    settings = get_settings()
    storage = build_storage(settings)
    orchestrator = AuditOrchestrator(settings, storage)

    all_cases = load_cases(args.cases)
    cases = select_cases(
        all_cases,
        framework=args.framework,
        start=args.start,
        limit=args.limit,
    )

    if not cases:
        raise SystemExit("No cases matched the requested filters.")

    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    if args.fresh_results:
        if CASE_RESULT_FILE.exists():
            CASE_RESULT_FILE.unlink()

        if SUMMARY_FILE.exists():
            SUMMARY_FILE.unlink()

    run_results: list[dict[str, Any]] = []

    print(
        json.dumps(
            {
                "cases_selected": len(cases),
                "framework": args.framework or "all",
                "start": args.start,
                "limit": args.limit,
                "runs": args.runs,
                "sleep_seconds": args.sleep,
            },
            indent=2,
        )
    )

    for index, case in enumerate(cases, start=1):
        print(
            f"\n[{index}/{len(cases)}] "
            f"{case['case_id']} · {case['framework']}"
        )

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

        started = time.perf_counter()

        envelope = orchestrator.run(
            document_id=case["document_id"],
            framework=case["framework"],
            runs=args.runs,
        )

        elapsed = time.perf_counter() - started

        predicted = {
            finding.rule_id
            for finding in envelope.report.findings
            if finding.status.value == "non_compliant"
        }
        expected = set(case["non_compliant_rule_ids"])
        score = precision_recall_f1(predicted, expected)

        result = {
            "case_id": case["case_id"],
            "framework": case["framework"],
            "predicted": sorted(predicted),
            "expected": sorted(expected),
            "precision": score.precision,
            "recall": score.recall,
            "f1": score.f1,
            "tp": score.tp,
            "fp": score.fp,
            "fn": score.fn,
            "faithfulness": envelope.judge.faithfulness,
            "completeness": envelope.judge.completeness,
            "hallucination_rate": envelope.judge.hallucination_rate,
            "consensus_agreement": envelope.consensus_agreement,
            "candidate_count": envelope.candidate_count,
            "tool_call_count": len(envelope.tool_trace),
            "latency_seconds": round(elapsed, 2),
        }

        run_results.append(result)
        append_case_result(result)

        print(json.dumps(result, indent=2))

        if index < len(cases):
            time.sleep(args.sleep)

    all_results = load_all_results()

    summary = build_summary(
        all_results
    )

    SUMMARY_FILE.write_text(
        json.dumps(
            summary,
            indent=2,
        ),
        encoding="utf-8",
)

    print("\nEVALUATION SUMMARY")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
