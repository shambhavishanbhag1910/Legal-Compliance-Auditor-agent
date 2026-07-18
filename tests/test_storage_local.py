from app.config import Settings
from app.storage import build_storage


def test_local_storage_save_and_load_document(tmp_path):
    settings = Settings(
        storage_backend="local",
        local_data_dir=str(tmp_path),
    )

    storage = build_storage(settings)

    storage.save_document(
        "doc-1",
        "hello compliance",
        {
            "document_id": "doc-1",
            "filename": "sample.txt",
        },
    )

    text, metadata = storage.load_document("doc-1")

    assert text == "hello compliance"
    assert metadata["filename"] == "sample.txt"