from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


ALLOWED_SUFFIXES = {".pdf", ".txt", ".md"}


def parse_document(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError(f"Unsupported file type: {suffix}. Allowed: {sorted(ALLOWED_SUFFIXES)}")

    if suffix == ".pdf":
        reader = PdfReader(BytesIO(content))
        pages = [(page.extract_text() or "") for page in reader.pages]
        text = "\n\n".join(pages)
    else:
        text = content.decode("utf-8", errors="replace")

    text = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if not text:
        raise ValueError("Document contains no extractable text.")
    return text


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[dict]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap.")

    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        candidate = text[start:end]
        if end < len(text):
            split_at = max(candidate.rfind("\n\n"), candidate.rfind(". "))
            if split_at > chunk_size // 2:
                end = start + split_at + (2 if candidate[split_at:split_at + 2] == ". " else 0)
                candidate = text[start:end]

        chunks.append({
            "chunk_id": f"chunk-{idx:04d}",
            "start": start,
            "end": end,
            "text": candidate.strip(),
        })
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
        idx += 1
    return chunks
