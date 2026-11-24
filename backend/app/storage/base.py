from abc import ABC, abstractmethod
from typing import Optional


class StorageProvider(ABC):
    """
    Abstract storage interface. Allows transparent switching between
    Local disk (dev), Azure Blob Storage, and Vercel Blob (production serverless).
    """

    @abstractmethod
    def save_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "image/png",
        folder: str = "sheets",
    ) -> str:
        """
        Saves file bytes and returns the stored path or public/signed URL.
        """
        pass

    @abstractmethod
    def get_file(self, file_path_or_url: str) -> Optional[bytes]:
        """
        Retrieves file bytes given a stored path or URL.
        """
        pass

    @abstractmethod
    def delete_file(self, file_path_or_url: str) -> bool:
        """
        Deletes a stored file.
        """
        pass
