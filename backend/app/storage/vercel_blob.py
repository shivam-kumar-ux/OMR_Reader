import os
import uuid
from typing import Optional
import httpx
from backend.app.storage.base import StorageProvider
from backend.app.core.config import settings


class VercelBlobStorageProvider(StorageProvider):
    """
    Vercel Blob Storage provider for production serverless deployments.
    Interacts via REST API using BLOB_READ_WRITE_TOKEN.
    """

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.BLOB_READ_WRITE_TOKEN

    def save_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "image/png",
        folder: str = "sheets",
    ) -> str:
        if not self.token:
            # Fallback to local if token not set
            from backend.app.storage.local import LocalStorageProvider
            return LocalStorageProvider().save_file(file_bytes, filename, content_type, folder)

        safe_name = f"{folder}/{uuid.uuid4().hex[:12]}_{os.path.basename(filename)}"
        url = f"https://blob.vercel-storage.com/{safe_name}"

        headers = {
            "Authorization": f"Bearer {self.token}",
            "x-content-type": content_type,
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.put(url, content=file_bytes, headers=headers)
            if resp.status_code in {200, 201}:
                data = resp.json()
                return data.get("url", url)
            else:
                raise RuntimeError(f"Vercel Blob upload failed: {resp.text}")

    def get_file(self, file_path_or_url: str) -> Optional[bytes]:
        if file_path_or_url.startswith("http://") or file_path_or_url.startswith("https://"):
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(file_path_or_url)
                if resp.status_code == 200:
                    return resp.content
                return None
        from backend.app.storage.local import LocalStorageProvider
        return LocalStorageProvider().get_file(file_path_or_url)

    def delete_file(self, file_path_or_url: str) -> bool:
        if not self.token:
            return True
        headers = {"Authorization": f"Bearer {self.token}"}
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                "https://blob.vercel-storage.com/delete",
                json={"urls": [file_path_or_url]},
                headers=headers,
            )
            return resp.status_code == 200
