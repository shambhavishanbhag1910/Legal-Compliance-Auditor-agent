import pytest

from app.config import Settings
from app.orchestrator import AuditOrchestrator
from app.storage import build_storage


def test_orchestrator_rejects_unknown_framework(tmp_path):
    settings = Settings(
        storage_backend="local",
        local_data_dir=str(tmp_path),
    )

    storage = build_storage(settings)

    storage.save_document(
        "doc-1",
        "sample document",
        {
            "document_id": "doc-1",
            "filename": "sample.txt",
        },
    )

    orchestrator = AuditOrchestrator(
        settings,
        storage,
    )

    with pytest.raises(ValueError):
        orchestrator.run(
            document_id="doc-1",
            framework="unknown",
            runs=3,
        )