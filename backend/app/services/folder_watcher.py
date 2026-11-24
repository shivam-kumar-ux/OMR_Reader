import os
import glob
import time
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.storage import get_storage_provider


class FolderWatcherService:
    """
    Watches the scanner input folder (STORAGE_WATCH_DIR) and processes new
    scanned files automatically.
    """

    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".webp", ".pdf"}

    def __init__(self, watch_dir: Optional[str] = None):
        self.watch_dir = os.path.abspath(watch_dir or settings.STORAGE_WATCH_DIR)
        os.makedirs(self.watch_dir, exist_ok=True)

    def scan_for_pending_files(self) -> List[str]:
        """
        Returns list of file paths ready for processing.
        """
        all_files = []
        for ext in self.SUPPORTED_EXTENSIONS:
            pattern = os.path.join(self.watch_dir, f"*{ext}")
            all_files.extend(glob.glob(pattern))
            pattern_upper = os.path.join(self.watch_dir, f"*{ext.upper()}")
            all_files.extend(glob.glob(pattern_upper))

        # Return unique sorted files
        return sorted(list(set(all_files)))

    def move_to_processed(self, file_path: str, subfolder: str = "archive") -> str:
        """
        Safely moves processed or failed files out of the hot incoming watch directory.
        """
        dest_dir = os.path.join(self.watch_dir, subfolder)
        os.makedirs(dest_dir, exist_ok=True)
        filename = os.path.basename(file_path)
        dest_path = os.path.join(dest_dir, f"{int(time.time())}_{filename}")
        os.rename(file_path, dest_path)
        return dest_path
