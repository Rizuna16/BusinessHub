import os
import uuid
from pathlib import Path


class StorageService:
    def __init__(self, upload_dir: str):
        self.upload_dir = upload_dir

    def _resolve_path(self, storage_key: str) -> Path:
        resolved = Path(self.upload_dir) / storage_key
        resolved = resolved.resolve()
        upload_root = Path(self.upload_dir).resolve()
        if not str(resolved).startswith(str(upload_root)):
            raise ValueError("Path traversal detected")
        return resolved

    def save_sync(self, storage_key: str, file_bytes: bytes) -> None:
        path = self._resolve_path(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(file_bytes)

    def delete_sync(self, storage_key: str) -> bool:
        path = self._resolve_path(storage_key)
        if path.exists():
            path.unlink()
            return True
        return False

    def exists_sync(self, storage_key: str) -> bool:
        path = self._resolve_path(storage_key)
        return path.exists()

    def generate_storage_key(self, business_id: str, product_id: str, variant_id: str | None, ext: str) -> str:
        file_id = str(uuid.uuid4())
        if variant_id:
            return f"{business_id}/products/{product_id}/variants/{variant_id}/{file_id}.{ext}"
        return f"{business_id}/products/{product_id}/{file_id}.{ext}"
