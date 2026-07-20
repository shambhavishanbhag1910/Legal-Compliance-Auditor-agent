# Architecture

AI Legal & Compliance Auditor is an evidence-first AI audit system for policy, legal, and compact financial disclosure documents.

It is designed to demonstrate practical AI engineering patterns: retrieval, tool use, structured outputs, self-consistency, independent judging, API design, frontend delivery, Docker, CI, and AWS deployment.

## Design Goals

The system is built around five principles:

1. Evidence before generation
2. Structured outputs instead of free-form reports
3. Auditable tool traces instead of hidden reasoning
4. Consensus across multiple candidates
5. Independent judge evaluation for faithfulness and hallucination risk

## Core Workflow

```text
Document Upload
      |
      v
Document Parser
      |
      v
Chunking
      |
      v
BM25 Evidence Index
      |
      v
Deterministic Rule Retrieval
      |
      v
Evidence Agent
      |
      v
Evidence Bundle
      |
      v
Structured Audit Candidates
      |
      v
Self-Consistency Consensus
      |
      v
Independent LLM Judge
      |
      v
Audit Envelope
      |
      v
Storage
```

## Application Components

| Component | Purpose |
|---|---|
| `app/main.py` | FastAPI API routes for health, document upload, audit creation, and audit retrieval |
| `app/main_with_ui.py` | FastAPI application with frontend routes mounted |
| `app/frontend.py` | Serves static frontend assets |
| `app/config.py` | Environment-driven application settings |
| `app/document_parser.py` | PDF, TXT, and Markdown parsing plus chunking |
| `app/search_index.py` | BM25 lexical retrieval over document chunks |
| `app/tools.py` | Search, chunk lookup, and glossary tools used by the evidence agent |
| `app/agent.py` | Evidence-gathering tool agent |
| `app/llm.py` | Groq OpenAI-compatible client for structured audit and judge calls |
| `app/consensus.py` | Majority-vote self-consistency logic |
| `app/judge.py` | Independent evaluation wrapper |
| `app/orchestrator.py` | End-to-end audit workflow coordination |
| `app/storage.py` | Local and S3 storage abstraction |
| `app/schemas.py` | Pydantic request, response, audit, and judge schemas |
| `app/frameworks.py` | Compact framework rule catalogs |
| `app/metrics.py` | Precision, recall, and F1 metrics |
| `frontend/` | Browser-based audit dashboard |
| `tests/` | Pytest-based validation |
| `scripts/` | Evaluation and deployment helpers |
| `infra/terraform/` | AWS infrastructure as code |
| `.github/workflows/ci.yml` | CI and Docker smoke testing |

## API Architecture

```text
Browser / API Client
        |
        v
FastAPI
        |
        +--> POST /documents
        |       |
        |       v
        |   parse + store document
        |
        +--> POST /audits
        |       |
        |       v
        |   run orchestrator
        |
        +--> GET /audits/{audit_id}
        |       |
        |       v
        |   load saved audit
        |
        +--> GET /health
                |
                v
            runtime status
```

## Evidence Retrieval Design

The system uses two evidence collection layers.

### 1. Deterministic Baseline Retrieval

For every framework rule, the system runs BM25 search against the document chunks. This ensures each rule receives basic retrieval coverage before any LLM-driven exploration.

### 2. Tool-Driven Evidence Agent

The evidence agent can call narrow read-only tools:

- `search_document`
- `get_chunk`
- `lookup_definition`

The agent does not execute arbitrary shell commands and does not mutate documents.

## Audit Generation Design

The audit flow generates multiple structured candidates. Each candidate must follow a Pydantic schema.

```text
Evidence Bundle
      |
      +--> Candidate 1
      +--> Candidate 2
      `--> Candidate 3
              |
              v
        Consensus Report
```

This helps reduce single-run instability and makes rule-level decisions more consistent.

## Consensus Design

Consensus is computed per rule ID:

1. collect candidate statuses
2. select the majority status
3. choose the strongest matching finding
4. resolve overall risk by majority
5. calculate agreement ratio

The output is a deterministic final audit report.

## Judge Design

After consensus, an independent judge evaluates the final report against the source document.

The judge returns:

- faithfulness
- completeness
- hallucination rate
- unsupported finding IDs
- fabricated claims
- comments

This makes the project stronger than a basic report generator because the system evaluates its own grounding quality.

## Storage Architecture

The storage layer supports two backends:

```text
Local Development
    |
    v
Local filesystem

AWS Deployment
    |
    v
Amazon S3
```

The same API and orchestrator use the storage abstraction, so the runtime can switch between local and S3 through environment variables.

## Frontend Architecture

The frontend provides:

- document upload
- framework selection
- audit execution
- progress display
- executive summary
- risk badge
- consensus metric
- judge metrics
- finding cards
- tool trace display

The current progress UI is partly simulated during synchronous execution. A production async job model should replace this with real job-stage progress.

## Docker Architecture

The Docker image packages:

- FastAPI backend
- frontend assets
- framework catalogs
- sample documents
- evaluation scripts

The container runs:

```text
uvicorn app.main_with_ui:app --host 0.0.0.0 --port 8000 --workers 2
```

## CI Architecture

GitHub Actions validates:

```text
Push / Pull Request
        |
        v
Install dependencies
        |
        v
Ruff lint
        |
        v
Pytest
        |
        v
Docker build
        |
        v
Container smoke test
        |
        +--> /health
        +--> /
        `--> /openapi.json
```

## AWS Cloud Architecture

```text
User Browser
    |
    v
Application Load Balancer
    |
    v
ECS Fargate Service
    |
    v
ECS Task: FastAPI + Frontend
    |
    +--> Amazon S3
    |
    +--> Groq API
    |
    `--> CloudWatch Logs
```

## AWS Services

| Service | Purpose |
|---|---|
| Amazon ECR | Stores Docker image |
| Amazon ECS Fargate | Runs the application container |
| Application Load Balancer | Public HTTP entry point |
| Amazon S3 | Stores documents and audit results |
| AWS Secrets Manager | Stores Groq API key |
| CloudWatch Logs | Captures ECS task logs |
| IAM | Execution role, task role, S3 and secret permissions |
| EC2 Security Groups | Controls ALB-to-task traffic |

## Security Architecture

Current protections:

- API key is stored in Secrets Manager for AWS deployment.
- API key is not committed to the repository.
- Uploaded files are restricted by type and size.
- S3 public access is blocked.
- Agent tools are narrow and read-only.
- No arbitrary shell execution is exposed.
- Outputs are schema constrained.
- Tool calls are traceable.

Production hardening still needed:

- authentication and authorization
- HTTPS with ACM certificate
- private subnets for ECS tasks
- WAF or API rate limiting
- structured JSON logging
- alerting on 5xx errors and ECS task failures
- tenant isolation for multi-user deployments

## Current Production Limitation

The current audit endpoint is synchronous:

```text
POST /audits
    |
    v
Run complete audit workflow
    |
    v
Return final audit result
```

This is simple and effective for local demos, but long-running LLM workflows should use asynchronous jobs:

```text
POST /audit-jobs
    |
    v
202 Accepted + job_id
    |
    v
Background Worker
    |
    v
GET /audit-jobs/{job_id}
    |
    v
GET /audits/{audit_id}
```

This will prevent browser and load-balancer timeout issues and allow real progress tracking.

## Future Target Architecture

```text
Browser
  |
  v
POST /audit-jobs
  |
  v
Job Queue
  |
  v
Worker
  |
  +--> Evidence Retrieval
  +--> LLM Candidate Generation
  +--> Consensus
  +--> Judge
  `--> S3 Audit Result
  |
  v
GET /audit-jobs/{job_id}
  |
  v
GET /audits/{audit_id}
```
