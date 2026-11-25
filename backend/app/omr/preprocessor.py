import os
from typing import List, Tuple, Dict, Any, Union
import cv2
import numpy as np


class QualityCheckResult:
    def __init__(self, passed: bool, reason: str = "", metrics: Dict[str, Any] = None):
        self.passed = passed
        self.reason = reason
        self.metrics = metrics or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "reason": self.reason,
            "metrics": self.metrics,
        }


class ImagePreprocessor:
    """
    Handles image loading, format normalization, PDF multi-page rendering,
    and automated image quality checks (blur, glare, darkness).
    """

    BLUR_THRESHOLD_VAR = 60.0  # Laplacian variance threshold
    DARKNESS_THRESHOLD_MEAN = 50.0  # Minimum mean luminance
    MAX_LUMINANCE_WASHED_OUT = 252.0  # Glare / overexposure threshold

    @classmethod
    def load_images_from_file_or_bytes(
        cls,
        file_bytes: bytes,
        filename: str = "",
    ) -> List[Tuple[np.ndarray, int]]:
        """
        Loads one or more sheet images from file bytes.
        If PDF, renders every page as a separate OpenCV BGR image.
        Returns list of (image_ndarray, page_number_1_based).
        """
        ext = os.path.splitext(filename)[1].lower() if filename else ""

        if ext == ".pdf" or file_bytes.startswith(b"%PDF-"):
            pages = []
            try:
                import pypdfium2 as pdfium
            except ImportError:
                raise ValueError("PDF rendering is not supported in the serverless deployment. Please upload PNG or JPEG sheet images.")
            try:
                pdf = pdfium.PdfDocument(file_bytes)
                for page_idx in range(len(pdf)):
                    page = pdf[page_idx]
                    bitmap = page.render(scale=2.77)
                    pil_image = bitmap.to_pil()
                    img_np = np.array(pil_image)
                    if len(img_np.shape) == 3 and img_np.shape[2] == 3:
                        bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                    elif len(img_np.shape) == 3 and img_np.shape[2] == 4:
                        bgr = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
                    else:
                        bgr = cv2.cvtColor(img_np, cv2.COLOR_GRAY2BGR)
                    pages.append((bgr, page_idx + 1))
            except Exception as e:
                raise ValueError(f"Failed to parse PDF document: {str(e)}")
            return pages

        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Unsupported or corrupted image file: {filename or 'unknown'}")

        return [(img, 1)]

    @classmethod
    def check_image_quality(cls, image: np.ndarray) -> QualityCheckResult:
        """
        Evaluates sheet image quality:
        - Glare / washed out (excessive overexposure where printed content disappears)
        - Darkness (mean luminance)
        - Blur (Laplacian variance)
        """
        if image is None or image.size == 0:
            return QualityCheckResult(False, "Empty or invalid image data")

        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        total_px = gray.size
        mean_lum = float(np.mean(gray))

        # Check for extreme glare / blank overexposure first
        # If image is almost entirely saturated white (>250) with virtually no ink/dark pixels (<180)
        dark_content_ratio = float(np.count_nonzero(gray < 180) / total_px)
        is_glare = mean_lum > cls.MAX_LUMINANCE_WASHED_OUT and dark_content_ratio < 0.005

        if is_glare:
            return QualityCheckResult(
                False,
                f"Quality check failed: Excessive glare or overexposure detected (mean luminance: {round(mean_lum, 1)})",
                {"mean_luminance": round(mean_lum, 2), "dark_content_ratio": round(dark_content_ratio, 4)},
            )

        # Darkness Check
        if mean_lum < cls.DARKNESS_THRESHOLD_MEAN:
            return QualityCheckResult(
                False,
                f"Quality check failed: Image is too dark (brightness: {round(mean_lum, 2)}, minimum required: {cls.DARKNESS_THRESHOLD_MEAN})",
                {"mean_luminance": round(mean_lum, 2)},
            )

        # Blur Check via Laplacian Variance
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        is_blurry = lap_var < cls.BLUR_THRESHOLD_VAR

        metrics = {
            "blur_variance": round(lap_var, 2),
            "mean_luminance": round(mean_lum, 2),
            "dark_content_ratio": round(dark_content_ratio, 4),
        }

        if is_blurry:
            return QualityCheckResult(
                False,
                f"Quality check failed: Image is blurry (sharpness score: {metrics['blur_variance']}, minimum required: {cls.BLUR_THRESHOLD_VAR})",
                metrics,
            )

        return QualityCheckResult(True, "Quality check passed", metrics)
