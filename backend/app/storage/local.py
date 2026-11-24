import os
import uuid
from typing import Optional
from backend.app.storage.base import StorageProvider
from backend.app.core.config import settings


class LocalStorageProvider(StorageProvider):
    """
    Local filesystem storage provider for local development and testing.
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = os.path.abspath(base_dir or settings.STORAGE_LOCAL_DIR)
        os.makedirs(self.base_dir, exist_ok=True)

    def save_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "image/png",
        folder: str = "sheets",
    ) -> str:
        target_dir = os.path.join(self.base_dir, folder)
        os.makedirs(target_dir, exist_ok=True)

        # Generate unique, safe filename
        ext = os.path.splitext(filename)[1].lower() or ".png"
        safe_name = f"{uuid.uuid4().hex[:12]}_{os.path.basename(filename)}"
        file_path = os.path.join(target_dir, safe_name)

        with open(file_path, "wb") as f:
            f.write(file_bytes)

        # Store relative path for portability
        rel_path = os.path.relpath(file_path, os.getcwd()).replace("\\", "/")
        return rel_path

    def get_file(self, file_path_or_url: str) -> Optional[bytes]:
        norm_path = os.path.abspath(file_path_or_url)
        if not os.path.exists(norm_path):
            # Try resolving relative to base_dir
            norm_path = os.path.join(self.base_dir, file_path_or_url.lstrip("/"))
            if not os.path.exists(norm_path):
                return None

        with open(norm_path, "rb") as f:
            return f.read()

    def delete_file(self, file_path_or_url: str) -> bool:
        norm_path = os.path.abspath(file_path_or_url)
        if os.path.exists(norm_path):
            os.remove(norm_path)
            return True
        return False
