from app.search_index import DocumentIndex


def test_search_returns_relevant_chunk():
    index = DocumentIndex([
        {"chunk_id": "c1", "text": "Users can request deletion of personal data."},
        {"chunk_id": "c2", "text": "Invoices are payable in thirty days."},
    ])
    results = index.search("privacy deletion request", top_k=1)
    assert results[0]["chunk_id"] == "c1"
