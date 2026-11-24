import base64
import difflib
import re
from typing import Dict, Any, List, Optional, Tuple
import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR


class OCREngine:
    """
    Lightweight ONNX-based OCR engine (RapidOCR) for handwriting cross-check.
    Crops handwritten boxes, filters via allow-list, compares with bubble values,
    and returns similarity scores and crops.
    """

    def __init__(self):
        # Lazy initialization
        self._ocr = None

    @property
    def ocr(self) -> RapidOCR:
        if self._ocr is None:
            self._ocr = RapidOCR()
        return self._ocr

    @staticmethod
    def calculate_similarity(s1: str, s2: str) -> float:
        """
        Calculates similarity ratio between two strings (0.0 to 1.0).
        Normalizes spaces and casing.
        """
        # Remove all spaces because boxed OCR outputs individual characters separated by spaces
        no_space1 = re.sub(r"\s+", "", (s1 or "").strip().upper())
        no_space2 = re.sub(r"\s+", "", (s2 or "").strip().upper())

        if not no_space1 and not no_space2:
            return 1.0
        if not no_space1 or not no_space2:
            return 0.0
        if no_space1 == no_space2:
            return 1.0

        return difflib.SequenceMatcher(None, no_space1, no_space2).ratio()

    def crop_field_boxes(
        self,
        image: np.ndarray,
        boxes: List[Dict[str, int]],
        padding: int = 4,
    ) -> Tuple[np.ndarray, str]:
        """
        Crops the entire bounding region containing the given list of handwritten boxes.
        Returns cropped BGR image and base64 JPEG data url.
        """
        if not boxes:
            empty = np.full((50, 100, 3), 255, dtype=np.uint8)
            return empty, ""

        h, w = image.shape[:2]
        min_x = max(min(b["x"] for b in boxes) - padding, 0)
        min_y = max(min(b["y"] for b in boxes) - padding, 0)
        max_x = min(max(b["x"] + b["width"] for b in boxes) + padding, w)
        max_y = min(max(b["y"] + b["height"] for b in boxes) + padding, h)

        crop = image[min_y:max_y, min_x:max_x].copy()
        if crop.size == 0:
            crop = np.full((50, 100, 3), 255, dtype=np.uint8)

        # Encode crop to base64 JPEG
        success, buf = cv2.imencode(".jpg", crop, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        b64_str = f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}" if success else ""

        return crop, b64_str

    def recognize_text(
        self,
        crop_image: np.ndarray,
        allow_digits_only: bool = False,
        allow_letters_only: bool = False,
    ) -> str:
        """
        Runs RapidOCR on the crop and filters by allow-list.
        """
        if crop_image is None or crop_image.size == 0:
            return ""

        # Preprocess crop: ensure minimum height of 48 px for accurate character segmentation
        ch, cw = crop_image.shape[:2]
        if ch < 48:
            scale = 48.0 / float(ch)
            crop_image = cv2.resize(
                crop_image, (int(cw * scale), 48), interpolation=cv2.INTER_CUBIC
            )

        # Pad with white border
        crop_image = cv2.copyMakeBorder(
            crop_image, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=[255, 255, 255]
        )

        try:
            results, _ = self.ocr(crop_image)
        except Exception:
            return ""

        if not results:
            return ""

        # Concatenate recognized texts
        extracted = []
        for line in results:
            if line and len(line) >= 2:
                text = line[1]
                if text:
                    extracted.append(str(text))

        raw_text = " ".join(extracted).strip().upper()

        # Apply allow-list filtering
        if allow_digits_only:
            # Common OCR confusions: O->0, I->1, S->5, B->8
            confusions = {"O": "0", "I": "1", "L": "1", "S": "5", "B": "8", "Z": "2", "G": "6"}
            for char, digit in confusions.items():
                raw_text = raw_text.replace(char, digit)
            filtered = re.sub(r"[^0-9]", "", raw_text)
            return filtered

        if allow_letters_only:
            # Common OCR confusions: 0->O, 1->I, 5->S, 8->B
            confusions = {"0": "O", "1": "I", "5": "S", "8": "B", "2": "Z"}
            for digit, char in confusions.items():
                raw_text = raw_text.replace(digit, char)
            filtered = re.sub(r"[^A-Z ]", "", raw_text)
            return re.sub(r"\s+", " ", filtered).strip()

        return raw_text

    def cross_check_field(
        self,
        aligned_image: np.ndarray,
        field_name: str,
        field_config: Dict[str, Any],
        bubble_value: str,
        similarity_threshold: float = 0.75,
    ) -> Dict[str, Any]:
        """
        Crops handwritten boxes, extracts OCR value, and computes similarity score.
        """
        boxes = field_config.get("handwritten_boxes", [])
        crop_img, crop_b64 = self.crop_field_boxes(aligned_image, boxes)

        field_type = field_config.get("type", "digits")
        digits_only = field_type == "digits" or field_name in {"roll_no", "mobile", "dob", "class_name"}
        letters_only = field_type == "letters" or field_name in {"name", "father_name", "set_code"}

        ocr_val = self.recognize_text(
            crop_img,
            allow_digits_only=digits_only,
            allow_letters_only=letters_only,
        )

        sim_score = self.calculate_similarity(bubble_value, ocr_val)

        # Bubble value is primary. If OCR is non-empty and similarity is below threshold, flag review
        match_passed = True
        reason = ""

        # For name fields: OCR cross-check rule
        if field_name == "name":
            if bubble_value and ocr_val and sim_score < similarity_threshold:
                match_passed = False
                reason = f"Name mismatch between bubbles ('{bubble_value}') and handwriting ('{ocr_val}') [similarity: {int(sim_score*100)}%]"

        elif field_name == "roll_no":
            # Bubbles are absolute ground truth for roll number.
            # If both exist and differ significantly, note reason for review
            if bubble_value and ocr_val and sim_score < 0.60:
                reason = f"Roll number handwriting check mismatch (Bubbles: {bubble_value}, Handwriting: {ocr_val})"

        return {
            "field_name": field_name,
            "bubble_value": bubble_value,
            "ocr_value": ocr_val,
            "similarity_score": round(sim_score, 4),
            "match_passed": match_passed,
            "reason": reason,
            "crop_image_base64": crop_b64,
        }
