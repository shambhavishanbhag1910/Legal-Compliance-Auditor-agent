# Frontend + 30-Document Evaluation Pack

This pack is intentionally non-destructive. It does not overwrite your working `agent.py`, `llm.py`, `schemas.py`, or existing API routes.

## 1. Copy the pack into the repository root

Merge these folders/files into your existing project:

- `app/frontend.py`
- `app/main_with_ui.py`
- `frontend/`
- `sample_docs/benchmark/`
- `eval/golden_cases_30.json`
- `eval/dataset_manifest.json`
- `eval/README_30_CASES.md`
- `scripts/run_eval_large.py`
- `Dockerfile.ui`
- `docker-compose.ui.yml`

## 2. Start the UI-enabled API

From the project root:

```powershell
uvicorn app.main_with_ui:app --reload --port 8000
```

Open:

```text
http://127.0.0.1:8000/
```

The existing API remains available:

- `GET /health`
- `POST /documents`
- `POST /audits`
- `GET /audits/{audit_id}`
- `GET /docs`

## 3. Run the 30-document benchmark in batches

The full set can be expensive on a low-TPM API tier. Use framework or batch filters.

### Privacy

```powershell
python -m scripts.run_eval_large --framework privacy --limit 5 --fresh-results
python -m scripts.run_eval_large --framework privacy --start 5
```

### Terms of Service

```powershell
python -m scripts.run_eval_large --framework tos
```

### Financial

```powershell
python -m scripts.run_eval_large --framework financial
```

### Small smoke batch

```powershell
python -m scripts.run_eval_large --limit 2 --fresh-results
```

Results:

- `eval_results/case_results.jsonl`
- `eval_results/latest_summary.json`

## 4. Run with Docker

```powershell
docker compose -f docker-compose.ui.yml up --build
```

Then open:

```text
http://127.0.0.1:8000/
```

## Dataset composition

| Framework | Documents | Typical omissions |
|---|---:|---|
| Privacy | 10 | retention, rights, sharing, security, contact |
| Terms of Service | 10 | termination, payment, acceptable use, liability, disputes |
| Financial | 10 | reporting period, revenue, risks, accounting basis, forward-looking uncertainty |

All documents are synthetic and created for testing. They are designed to be realistic without copying real policies or filings.
