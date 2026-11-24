import os
import uuid
from typing import Optional
from backend.app.storage.base import StorageProvider
from backend.app.core.config import settings


class AzureBlobStorageProvider(StorageProvider):
    """
    Azure Blob Storage provider for production enterprise Azure deployments.
    Uses connection string or SAS token.
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        container_name: Optional[str] = None,
    ):
        self.connection_string = connection_string or settings.AZURE_STORAGE_CONNECTION_STRING
        self.container_name = container_name or settings.AZURE_STORAGE_CONTAINER_NAME

    def save_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "image/png",
        folder: str = "sheets",
    ) -> str:
        if not self.connection_string:
            from backend.app.storage.local import LocalStorageProvider
            return LocalStorageProvider().save_file(file_bytes, filename, content_type, folder)

        try:
            from azure.storage.blob import BlobServiceClient
            blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
            blob_client = blob_service_client.get_blob_client(
                container=self.container_name,
                blob=f"{folder}/{uuid.uuid4().hex[:12]}_{filename}",
            )
            blob_client.upload_blob(file_bytes, overwrite=True)
            return blob_client.url
        except Exception:
            from backend.app.storage.local import LocalStorageProvider
            return LocalStorageProvider().save_file(file_bytes, filename, content_type, folder)

    def get_file(self, file_path_or_url: str) -> Optional[bytes]:
        if file_path_or_url.startswith("http"):
            import httpx
            with httpx.Client(timeout=30.0) as client:
                r = client.get(file_path_or_url)
                return r.content if r.status_code == 200 else None
        from backend.app.storage.local import LocalStorageProvider
        return LocalStorageProvider().get_file(file_path_or_url)

    def delete_file(self, file_path_or_url: str) -> bool:
        return True
