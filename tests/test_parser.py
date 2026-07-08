from app.document_parser import chunk_text, parse_document


def test_parse_text_document():
    assert parse_document("sample.txt", b"hello compliance") == "hello compliance"


def test_chunk_text_has_ids():
    chunks = chunk_text("A" * 3000, chunk_size=1000, overlap=100)
    assert len(chunks) >= 3
    assert chunks[0]["chunk_id"] == "chunk-0000"
