from backend.app.core.config import settings
from backend.app.storage.base import StorageProvider
from backend.app.storage.local import LocalStorageProvider
from backend.app.storage.vercel_blob import VercelBlobStorageProvider
from backend.app.storage.azure_blob import AzureBlobStorageProvider


def get_storage_provider() -> StorageProvider:
    provider = settings.STORAGE_PROVIDER.lower()
    if provider == "vercel_blob":
        return VercelBlobStorageProvider()
    elif provider == "azure_blob":
        return AzureBlobStorageProvider()
    return LocalStorageProvider()


__all__ = [
    "StorageProvider",
    "LocalStorageProvider",
    "VercelBlobStorageProvider",
    "AzureBlobStorageProvider",
    "get_storage_provider",
]
