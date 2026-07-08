# 30-Case Synthetic Compliance Benchmark

This benchmark contains 30 synthetic but realistic business documents:

- 10 privacy notices
- 10 terms-of-service documents
- 10 financial management-review documents

The documents are designed for portfolio evaluation and testing. They do not copy real company policies or filings.

## Design principle

A rule is labeled `non_compliant` when the document deliberately omits the required disclosure. The documents generally avoid explicit statements such as "this policy does not contain retention terms." This forces the system to reason from document coverage rather than from an artificially obvious sentence.

## Files

- `golden_cases_30.json`: evaluation case list consumed by `scripts/run_eval_large.py`
- `dataset_manifest.json`: case metadata and organization names
- `sample_docs/benchmark/privacy/`: 10 privacy notices
- `sample_docs/benchmark/tos/`: 10 Terms of Service
- `sample_docs/benchmark/financial/`: 10 financial reviews

## Recommended evaluation strategy

Do not run all 30 cases at once on a low-TPM API tier. Run in batches:

```powershell
python -m scripts.run_eval_large --framework privacy --limit 5
python -m scripts.run_eval_large --framework privacy --start 5
python -m scripts.run_eval_large --framework tos
python -m scripts.run_eval_large --framework financial
```

Results are appended to `eval_results/case_results.jsonl` and the latest aggregate summary is written to `eval_results/latest_summary.json`.
