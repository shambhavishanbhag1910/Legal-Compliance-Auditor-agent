from uuid import uuid4
import logging
from fastapi import FastAPI, File, HTTPException, UploadFile

from app.config import get_settings
from app.document_parser import parse_document
from app.orchestrator import AuditOrchestrator
from app.schemas import AuditEnvelope, AuditRequest, DocumentCreated
from app.storage import build_storage

logger = logging.getLogger(__name__)

settings = get_settings()
storage = build_storage(settings)

app = FastAPI(
    title="AI Legal & Compliance Auditor",
    version="1.0.0",
    description=(
        "Educational AI audit pipeline with tool use, self-consistency, "
        "structured output, and LLM evaluation."
    ),
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "healthy",
        "storage_backend": settings.storage_backend,
        "model_configured": bool(settings.groq_model),
        "api_key_configured": bool(settings.groq_api_key.get_secret_value()),
    }


@app.post("/documents", response_model=DocumentCreated)
async def create_document(file: UploadFile = File(...)) -> DocumentCreated:
    filename = file.filename or "document.txt"
    content = await file.read()

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.max_upload_mb} MB limit.",
        )

    try:
        text = parse_document(filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    document_id = str(uuid4())
    metadata = {
        "document_id": document_id,
        "filename": filename,
        "characters": len(text),
    }
    storage.save_document(document_id, text, metadata)
    return DocumentCreated(**metadata)


@app.post(
    "/audits",
    response_model=AuditEnvelope,
)
def create_audit(
    request: AuditRequest,
) -> AuditEnvelope:
    try:
        orchestrator = AuditOrchestrator(
            settings,
            storage,
        )

        return orchestrator.run(
            document_id=request.document_id,
            framework=request.framework,
            runs=request.runs,
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        ) from exc

    except Exception as exc:
        logger.exception(
            "Audit pipeline failed"
        )

        raise HTTPException(
            status_code=500,
            detail={
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
        ) from exc


@app.get("/audits/{audit_id}", response_model=AuditEnvelope)
def get_audit(audit_id: str) -> AuditEnvelope:
    try:
        payload = storage.load_audit(audit_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Audit not found.") from exc
    return AuditEnvelope.model_validate(payload)
