import json

from app.frameworks import DEFINITIONS
from app.search_index import DocumentIndex
from openai.types.responses import ToolParam

TOOL_DEFINITIONS: list[ToolParam] = [
    {
        "type": "function",
        "name": "search_document",
        "description": "Search the current source document for evidence relevant to a compliance requirement.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 8},
                "purpose": {
                    "type": "string",
                    "description": "Short audit rationale describing the evidence being sought. Do not provide private chain-of-thought.",
                },
            },
            "required": ["query", "top_k", "purpose"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_chunk",
        "description": "Read one exact document chunk by chunk ID after discovering it with search_document.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "chunk_id": {"type": "string"},
                "purpose": {"type": "string", "description": "Short audit rationale for reading the chunk."},
            },
            "required": ["chunk_id", "purpose"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "lookup_definition",
        "description": "Look up a small built-in compliance definition.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "term": {"type": "string"},
                "purpose": {"type": "string", "description": "Short reason the definition is relevant."},
            },
            "required": ["term", "purpose"],
            "additionalProperties": False,
        },
    },
]


class AuditToolRegistry:
    def __init__(self, index: DocumentIndex):
        self.index = index
        self.seen_chunks = {}

    def execute(self, name: str, arguments_json: str) -> tuple[dict, str]:
        args = json.loads(arguments_json)
        purpose = str(args.get("purpose", ""))

        if name == "search_document":
            results = self.index.search(args["query"], int(args["top_k"]))
            for item in results:
                self.seen_chunks[item["chunk_id"]] = item
            return {"results": results}, purpose

        if name == "get_chunk":
            chunk = self.index.get_chunk(args["chunk_id"])
            self.seen_chunks[chunk["chunk_id"]] = chunk
            return {"chunk": chunk}, purpose

        if name == "lookup_definition":
            term = args["term"].strip().lower()
            return {
                "term": term,
                "definition": DEFINITIONS.get(term, "Definition not available in the built-in glossary."),
            }, purpose

        raise ValueError(f"Unknown tool: {name}")

    def evidence_bundle(self) -> list[dict]:
        return list(self.seen_chunks.values())
