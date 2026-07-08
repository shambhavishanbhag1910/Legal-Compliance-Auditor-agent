import json
from pathlib import Path
from typing import Protocol

import boto3

from app.config import Settings


class Storage(Protocol):
    def save_document(self, document_id: str, text: str, metadata: dict) -> None: ...
    def load_document(self, document_id: str) -> tuple[str, dict]: ...
    def save_audit(self, audit_id: str, payload: dict) -> None: ...
    def load_audit(self, audit_id: str) -> dict: ...


class LocalStorage:
    def __init__(self, base_dir: str):
        self.base = Path(base_dir)
        (self.base / "documents").mkdir(parents=True, exist_ok=True)
        (self.base / "audits").mkdir(parents=True, exist_ok=True)

    def save_document(self, document_id: str, text: str, metadata: dict) -> None:
        (self.base / "documents" / f"{document_id}.txt").write_text(text, encoding="utf-8")
        (self.base / "documents" / f"{document_id}.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )

    def load_document(self, document_id: str) -> tuple[str, dict]:
        text_path = self.base / "documents" / f"{document_id}.txt"
        meta_path = self.base / "documents" / f"{document_id}.json"
        if not text_path.exists() or not meta_path.exists():
            raise FileNotFoundError(document_id)
        return text_path.read_text(encoding="utf-8"), json.loads(meta_path.read_text(encoding="utf-8"))

    def save_audit(self, audit_id: str, payload: dict) -> None:
        (self.base / "audits" / f"{audit_id}.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    def load_audit(self, audit_id: str) -> dict:
        path = self.base / "audits" / f"{audit_id}.json"
        if not path.exists():
            raise FileNotFoundError(audit_id)
        return json.loads(path.read_text(encoding="utf-8"))


class S3Storage:
    def __init__(self, bucket: str, region: str):
        if not bucket:
            raise ValueError("S3_BUCKET is required when STORAGE_BACKEND=s3.")
        self.bucket = bucket
        self.client = boto3.client("s3", region_name=region)

    def _put(self, key: str, body: str) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body.encode("utf-8"),
            ContentType="application/json" if key.endswith(".json") else "text/plain",
            ServerSideEncryption="AES256",
        )

    def _get(self, key: str) -> str:
        try:
            obj = self.client.get_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            if "NoSuchKey" in str(exc) or "404" in str(exc):
                raise FileNotFoundError(key) from exc
            raise
        return obj["Body"].read().decode("utf-8")

    def save_document(self, document_id: str, text: str, metadata: dict) -> None:
        self._put(f"documents/{document_id}.txt", text)
        self._put(f"documents/{document_id}.json", json.dumps(metadata))

    def load_document(self, document_id: str) -> tuple[str, dict]:
        try:
            return (
                self._get(f"documents/{document_id}.txt"),
                json.loads(self._get(f"documents/{document_id}.json")),
            )
        except FileNotFoundError as exc:
            raise FileNotFoundError(document_id) from exc

    def save_audit(self, audit_id: str, payload: dict) -> None:
        self._put(f"audits/{audit_id}.json", json.dumps(payload))

    def load_audit(self, audit_id: str) -> dict:
        try:
            return json.loads(self._get(f"audits/{audit_id}.json"))
        except FileNotFoundError as exc:
            raise FileNotFoundError(audit_id) from exc


def build_storage(settings: Settings) -> Storage:
    if settings.storage_backend.lower() == "s3":
        return S3Storage(settings.s3_bucket, settings.aws_region)
    return LocalStorage(settings.local_data_dir)
