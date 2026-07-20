# Roadmap

This roadmap describes the next steps required to move AI Legal & Compliance Auditor from a strong portfolio-grade project toward a more production-ready system.

## Current Status

The project currently includes:

- FastAPI backend
- frontend audit dashboard
- document upload and parsing
- BM25 retrieval
- evidence agent with read-only tools
- structured audit generation
- self-consistency consensus
- independent LLM-as-Judge evaluation
- local and S3 storage support
- Docker and Docker Compose
- GitHub Actions CI
- Terraform AWS deployment
- ECS Fargate runtime
- Application Load Balancer
- S3, Secrets Manager, and CloudWatch integration

The highest-priority production gap is asynchronous audit execution.

## Priority 1: Asynchronous Audit Execution

The current `/audits` endpoint runs synchronously. This is simple for local demos, but not ideal for cloud execution because audits can involve several LLM calls and tool rounds.

### Target Design

```text
POST /audit-jobs
    |
    v
202 Accepted
{
  "job_id": "...",
  "status": "queued"
}

GET /audit-jobs/{job_id}
    |
    v
{
  "status": "running",
  "stage": "evidence_collection",
  "progress": 40
}

GET /audits/{audit_id}
    |
    v
Final audit result
```

### Required Changes

- Add `AuditJob` schema.
- Add job status enum: `queued`, `running`, `completed`, `failed`.
- Add job stage field: `upload`, `evidence_collection`, `candidate_generation`, `consensus`, `judge`, `completed`.
- Add job progress field from 0 to 100.
- Add job metadata storage using local filesystem or S3.
- Add background worker execution.
- Add `POST /audit-jobs` endpoint.
- Add `GET /audit-jobs/{job_id}` endpoint.
- Keep `GET /audits/{audit_id}` for final audit retrieval.
- Update frontend to poll job status.
- Replace simulated progress with real backend progress.
- Add error details for failed jobs.

### Candidate Implementation Options

Option 1: FastAPI `BackgroundTasks`

- Simple to implement
- Good for portfolio demo
- Not ideal for multi-instance production

Option 2: Celery or RQ worker

- More production-like
- Requires Redis or another queue backend
- Better for long-running jobs

Option 3: AWS-native workflow

- SQS for queue
- ECS worker service for processing
- S3 or DynamoDB for job state
- CloudWatch alarms for failures

Recommended next step: implement FastAPI `BackgroundTasks` first, then document a future SQS/ECS worker design.

## Priority 2: Stronger Test Coverage

Current tests should be expanded to cover more of the system without calling the live LLM.

### Add API Tests

- `POST /documents` with TXT file
- `POST /documents` with unsupported file type
- `POST /documents` with oversized file
- `GET /audits/{audit_id}` for missing audit
- `/health` response shape

### Add Storage Tests

- local document save/load
- local audit save/load
- missing document behavior
- missing audit behavior
- S3 storage mocked with Moto or botocore stubs

### Add Orchestrator Tests

Use mocked LLM and mocked agent behavior to test:

- invalid framework handling
- empty evidence handling
- successful envelope creation
- judge result included
- audit saved after completion

### Add Frontend Smoke Tests

- root route returns HTML
- static CSS loads
- static JS loads

## Priority 3: Evaluation Expansion

The evaluation system should become more rigorous.

### Add More Cases

- larger privacy policies
- terms of service examples
- financial disclosure examples
- mixed compliant/non-compliant documents
- ambiguous clauses
- missing-data cases

### Add Adversarial Cases

- prompt injection inside uploaded document
- contradictory clauses
- irrelevant legal text
- misleading headings
- repeated boilerplate

### Add Retrieval Metrics

- Recall@K
- MRR
- evidence coverage by rule
- missing evidence rate

### Add Report Quality Metrics

- unsupported finding rate
- fabricated claim count
- judge faithfulness trend
- judge completeness trend
- consensus agreement trend

## Priority 4: Production Hardening

The current cloud deployment is suitable for demonstration and architecture validation. Production requires additional hardening.

### Security

- Add authentication.
- Add authorization for audit access.
- Add HTTPS using ACM certificate.
- Add WAF or rate limiting.
- Add request size limits at ALB/API level.
- Add tenant isolation for multi-user use.
- Add audit access logging.

### Infrastructure

- Move ECS tasks to private subnets.
- Use NAT Gateway or VPC endpoints where appropriate.
- Add autoscaling policy.
- Add Terraform variables for environment names.
- Add remote Terraform state backend.
- Add separate dev/stage/prod workspaces.

### Observability

- Add structured JSON logs.
- Add correlation IDs.
- Add audit/job IDs to logs.
- Add CloudWatch metrics.
- Add alarms for ECS task failures.
- Add alarms for ALB 5xx responses.
- Add alarms for high latency.

## Priority 5: Frontend Improvements

The frontend should evolve from demo dashboard to operational workflow.

Recommended improvements:

- real job progress polling
- audit history page
- upload validation before submit
- finding search and filters
- export audit report to JSON/PDF
- show evidence snippets beside each finding
- show tool trace in expandable timeline
- show judge warnings prominently

## Priority 6: Model and Prompt Improvements

Recommended improvements:

- separate generation model and judge model
- add prompt versioning
- store prompt metadata with each audit
- add model latency and token usage tracking
- add retry strategy metrics
- add fallback behavior for rate limits
- add configurable candidate count

## Priority 7: Data and Compliance Scope

The current framework catalogs are compact and demo-oriented.

Future improvements:

- expand framework rules
- add jurisdiction-specific catalogs
- version framework catalogs
- cite rule source metadata
- add policy-specific glossary
- support custom user-defined frameworks

## Suggested Milestone Plan

### Milestone 1: Async Demo Upgrade

- Add job schema
- Add background task execution
- Add job status endpoint
- Update frontend polling
- Add tests for job lifecycle

### Milestone 2: Test and Evaluation Upgrade

- Add mocked LLM orchestrator tests
- Add storage tests
- Add retrieval metrics
- Add prompt injection cases

### Milestone 3: Cloud Hardening

- Add HTTPS
- Add authentication
- Move ECS tasks to private subnets
- Add structured logs and CloudWatch alarms

### Milestone 4: Portfolio Polish

- Add screenshots
- Add architecture diagram image
- Add sample audit output
- Add benchmark summary
- Add short demo video link

## Final Target

The target system should support this production-grade flow:

```text
User uploads document
      |
      v
System creates async audit job
      |
      v
Worker performs evidence-grounded audit
      |
      v
System stores audit result
      |
      v
Frontend shows final report with evidence, consensus, and judge metrics
      |
      v
User exports report
```
