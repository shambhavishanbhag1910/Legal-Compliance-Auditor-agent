import re

from rank_bm25 import BM25Okapi


TOKEN_RE = re.compile(r"[A-Za-z0-9_'-]+")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


class DocumentIndex:
    def __init__(self, chunks: list[dict]):
        if not chunks:
            raise ValueError("At least one chunk is required.")
        self.chunks = chunks
        self.by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
        self.bm25 = BM25Okapi([tokenize(chunk["text"]) for chunk in chunks])

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        top_k = max(1, min(top_k, 8))
        scores = self.bm25.get_scores(tokenize(query))
        ranked = sorted(zip(self.chunks, scores), key=lambda x: float(x[1]), reverse=True)[:top_k]
        return [
            {"chunk_id": chunk["chunk_id"], "score": round(float(score), 4), "text": chunk["text"]}
            for chunk, score in ranked
        ]

    def get_chunk(self, chunk_id: str) -> dict:
        if chunk_id not in self.by_id:
            raise KeyError(f"Unknown chunk_id: {chunk_id}")
        return self.by_id[chunk_id]
