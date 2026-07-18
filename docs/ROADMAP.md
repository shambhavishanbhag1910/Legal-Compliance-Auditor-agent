# Roadmap

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