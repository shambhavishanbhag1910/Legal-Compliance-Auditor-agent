# AI Legal & Compliance Auditor

AI Legal & Compliance Auditor is an evidence-first audit system for policy, legal, and compact financial disclosure documents.

The system reads a document, builds a local evidence index, uses a tool-driven evidence agent, generates multiple schema-constrained audit candidates, applies self-consistency consensus, and evaluates the final report for faithfulness, completeness, and hallucination risk.

This project demonstrates an end-to-end AI engineering workflow from local development to Docker, CI, Terraform, and AWS ECS Fargate deployment.

## Why This Project Matters

Many LLM audit demos generate fluent reports without proving where the answer came from. This project is designed differently:

- Evidence is collected before report generation.
- Tool calls are recorded as an auditable trace.
- Final outputs are constrained by Pydantic schemas.
- Multiple audit candidates are reconciled through consensus.
- A separate judge evaluates faithfulness and hallucination risk.
- The system supports both local storage and S3-backed cloud deployment.

## Architecture

```text
Raw Document
    |
    v
Document Parser + Chunk Index
    |
    v
BM25 Evidence Retrieval
    |
    v
ReAct-style Evidence Agent
    |-- search_document
    |-- get_chunk
    `-- lookup_definition
    |
    v
Evidence Bundle
    |
    +--> Structured Audit Candidate 1
    +--> Structured Audit Candidate 2
    `--> Structured Audit Candidate 3
                    |
                    v
         Self-Consistency Consensus
                    |
                    v
         Strict Pydantic JSON Report
                    |
                    v
              LLM-as-a-Judge
                    |
                    v
 Faithfulness | Completeness | Hallucination Rate
```

The implementation deliberately does not expose private chain-of-thought. The agent records an auditable action trace containing the tool name, arguments, declared evidence purpose, and a result preview.

## Features

- FastAPI REST API
- Browser-based frontend audit dashboard
- PDF, TXT, and Markdown ingestion
- BM25 document search
- Deterministic baseline retrieval for framework rules
- ReAct-style iterative evidence collection
- Groq OpenAI-compatible SDK endpoint
- Tool calling for document search and chunk lookup
- Strict Pydantic structured outputs
- Three-run self-consistency voting
- Independent LLM-as-a-Judge evaluation
- Precision, recall, and F1 evaluation on golden cases
- Local filesystem storage for development
- Amazon S3 persistence for AWS deployment
- Docker and Docker Compose
- Pytest-based test suite
- GitHub Actions CI
- Terraform deployment to Amazon ECS Fargate
- Amazon ECR image registry
- Application Load Balancer
- AWS Secrets Manager integration
- CloudWatch Logs

## End-to-End Project Status

This project demonstrates an evidence-first AI Legal and Compliance Auditor with:

- FastAPI backend
- Frontend audit dashboard
- Document upload and parsing
- Local BM25 evidence retrieval
- Tool-driven evidence collection
- Structured audit generation
- Self-consistency consensus
- Independent LLM-as-Judge evaluation
- Dockerized deployment
- GitHub Actions CI
- Terraform Infrastructure as Code
- AWS ECS Fargate deployment
- Amazon ECR image registry
- Application Load Balancer
- Amazon S3 document and audit storage
- AWS Secrets Manager for Groq API key
- CloudWatch logging

Verified deployment status:

- Frontend: working
- `/health`: working
- Storage backend: S3
- Model provider: Groq OpenAI-compatible API endpoint
- Full long-running audit execution: recommended to move to async jobs for production-grade cloud use

## Project Structure

```text
ai_legal_compliance_auditor/
├── app/
│   ├── agent.py
│   ├── config.py
│   ├── consensus.py
│   ├── document_parser.py
│   ├── frameworks.py
│   ├── judge.py
│   ├── llm.py
│   ├── main.py
│   ├── main_with_ui.py
│   ├── metrics.py
│   ├── orchestrator.py
│   ├── schemas.py
│   ├── search_index.py
│   ├── storage.py
│   └── tools.py
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT.md
│   └── ROADMAP.md
├── eval/
│   └── golden_cases.json
├── frontend/
├── infra/
│   └── terraform/
├── sample_docs/
├── scripts/
├── tests/
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── requirements-dev.txt
```

## Included Framework Catalogs

The project includes compact demonstration catalogs for:

- privacy policies
- terms of service
- financial disclosure documents

These catalogs demonstrate the architecture and evaluation workflow. They are not a substitute for jurisdiction-specific legal requirements.

## Known Production Limitation

The current `/audits` endpoint runs the full audit synchronously:

1. Evidence collection
2. Multi-candidate audit generation
3. Consensus
4. Independent judge evaluation
5. Audit persistence

This works for local testing and controlled demos, but long-running cloud execution should be moved to an asynchronous job architecture.

Recommended production upgrade:

- `POST /audit-jobs` returns `202 Accepted` with a `job_id`
- Background worker performs audit execution
- `GET /audit-jobs/{job_id}` returns status and progress
- Frontend polls job status or uses Server-Sent Events
- Completed audit is fetched by `audit_id`

This avoids browser and load-balancer timeout issues for larger documents and multi-step reasoning flows.

## Local Setup

### 1. Create a virtual environment

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements-dev.txt
```

### 3. Configure environment

Windows:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

Set these values in `.env`:

```text
GROQ_API_KEY=your_groq_key
GROQ_MODEL=openai/gpt-oss-20b
GROQ_BASE_URL=https://api.groq.com/openai/v1
STORAGE_BACKEND=local
LOCAL_DATA_DIR=data
SELF_CONSISTENCY_RUNS=3
MAX_TOOL_STEPS=2
MAX_UPLOAD_MB=10
```

### 4. Start the full frontend + API app

```bash
uvicorn app.main_with_ui:app --reload --port 8000
```

Open the frontend:

```text
http://127.0.0.1:8000/
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
http://127.0.0.1:8000/health
```

## Docker

Build and run with Docker Compose:

```bash
docker compose up --build
```

Open:

```text
http://127.0.0.1:8000/
```

The Docker image runs:

```text
uvicorn app.main_with_ui:app --host 0.0.0.0 --port 8000 --workers 2
```

## API Flow

### 1. Upload a document

```bash
curl -X POST "http://127.0.0.1:8000/documents" \
  -F "file=@sample_docs/privacy_policy_acme.txt"
```

The response contains:

```json
{
  "document_id": "...",
  "filename": "privacy_policy_acme.txt",
  "characters": 1234
}
```

### 2. Run an audit

```bash
curl -X POST "http://127.0.0.1:8000/audits" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "REPLACE_ME",
    "framework": "privacy",
    "runs": 3
  }'
```

The response contains:

- final consensus report
- consensus agreement score
- tool action trace
- judge scores
- unsupported finding IDs
- fabricated claims
- candidate count

### 3. Read a saved audit

```text
GET /audits/{audit_id}
```

### 4. Health check

```text
GET /health
```

Expected health response:

```json
{
  "status": "healthy",
  "storage_backend": "local",
  "model_configured": true,
  "api_key_configured": true
}
```

## Self-Consistency Strategy

Each audit uses one evidence-gathering pass followed by multiple independent structured extraction passes.

Consensus is computed per rule ID:

1. collect candidate statuses
2. choose the majority status
3. select the strongest matching finding
4. use majority risk rating
5. calculate agreement ratio

The consensus layer is deterministic and unit tested.

## Evaluation

Run the default evaluation:

```bash
python scripts/run_eval.py
```

For the larger benchmark runner, use:

```bash
python scripts/run_eval_large.py --runs 3
```

The golden dataset is stored in:

```text
eval/golden_cases.json
```

Evaluation calculates:

```text
Precision
Recall
F1
```

The predicted positive set is the set of rule IDs classified as `non_compliant`.

A separate LLM judge scores:

```text
faithfulness
completeness
hallucination_rate
unsupported_finding_ids
fabricated_claims
```

## Prompt Engineering Concepts Demonstrated

| Concept | Implementation |
|---|---|
| Zero-shot prompting | Framework-based audit instructions |
| ReAct | Iterative evidence tool loop |
| Tool calling | Search, exact chunk read, glossary lookup |
| Structured output | Pydantic `AuditReport` and `JudgeResult` |
| Self-consistency | Three candidates plus majority consensus |
| Meta prompting | Framework rules inserted dynamically |
| LLM-as-a-Judge | Separate source-grounded evaluation pass |
| Evidence grounding | Audit findings tied back to retrieved chunks |

## AWS Deployment

The application is containerized and deployed on AWS using:

- Docker
- Amazon ECR
- Amazon ECS Fargate
- Application Load Balancer
- Amazon S3 for document and audit storage
- AWS Secrets Manager for Groq API key
- Amazon CloudWatch Logs
- Terraform Infrastructure as Code

Health check:

```text
GET /health
```

Runtime storage backend:

```text
s3
```

Detailed deployment steps are available in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Cloud Architecture Summary

The Terraform stack provisions:

```text
ECR
  |
  v
ECS Fargate Service
  |
  v
Application Load Balancer
  |
  v
Public Frontend + API

S3
  |
  +-- documents
  `-- audit results

Secrets Manager
  |
  `-- GROQ_API_KEY

CloudWatch Logs
```

## Security Notes

- The API key is not committed.
- AWS deployment injects the key from Secrets Manager.
- Uploaded files are restricted by type and size.
- Agent tools are narrow and read-only.
- No arbitrary shell execution is exposed.
- Search results and tool iterations are bounded.
- Final reports and judge results are schema constrained.
- Terraform blocks public S3 access.
- The current public demo deployment should not be treated as hardened production.

## Tests

Run lint and tests:

```bash
ruff check app tests scripts
pytest -q
```

The test suite is intended to cover:

- API health checks
- document parsing
- chunking
- BM25 retrieval
- self-consistency majority voting
- precision, recall, and F1 metrics
- local storage behavior
- selected API and orchestration failure paths

## CI

GitHub Actions validates:

- dependency installation
- Ruff linting
- Pytest test suite
- Docker image build
- container startup
- `/health` endpoint
- frontend route
- OpenAPI route

## Documentation

Additional documentation:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
- [`docs/ROADMAP.md`](docs/ROADMAP.md)

## Roadmap

See [`docs/ROADMAP.md`](docs/ROADMAP.md).

Highest-priority production upgrade:

- move synchronous `/audits` execution to asynchronous audit jobs
- return `job_id`
- process audit in a background worker
- expose job status endpoint
- update frontend with real progress polling

## Disclaimer

This project is an AI engineering and compliance-audit demonstration. It is not legal advice and should not be used as a substitute for review by qualified legal, compliance, or regulatory professionals.
