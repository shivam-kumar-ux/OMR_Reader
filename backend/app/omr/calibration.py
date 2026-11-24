import json
import os
from typing import Dict, Any, Tuple
import cv2
import numpy as np


class OMRCalibrator:
    """
    Visual calibration engine that overlays template definitions onto
    blank or aligned OMR sheets to verify coordinate accuracy.
    """

    def __init__(self, template_path: str = "./backend/app/omr/templates/standard_omr_template.json"):
        self.template_path = template_path
        self.template = self.load_template(template_path)

    @staticmethod
    def load_template(path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Template file not found at {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def overlay_calibration(
        self,
        image: np.ndarray,
        template: Dict[str, Any] = None,
        draw_labels: bool = True,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Overlays template coordinates on top of an image.
        Returns:
            annotated_image: np.ndarray (BGR)
            stats: summary of drawn components
        """
        if template is None:
            template = self.template

        overlay = image.copy()
        if len(overlay.shape) == 2:
            overlay = cv2.cvtColor(overlay, cv2.COLOR_GRAY2BGR)

        stats = {
            "corner_markers_count": 0,
            "handwritten_boxes_count": 0,
            "personal_bubbles_count": 0,
            "answer_bubbles_count": 0,
            "total_questions": 0,
            "is_valid": True,
        }

        # 1. Overlay Corner Markers (Red)
        corner_markers = template.get("corner_markers", {})
        for name, data in corner_markers.items():
            cx, cy = data["center"]
            w, h = data["width"], data["height"]
            cv2.rectangle(overlay, (data["x"], data["y"]), (data["x"] + w, data["y"] + h), (0, 0, 255), 2)
            cv2.drawMarker(overlay, (cx, cy), (0, 0, 255), markerType=cv2.MARKER_CROSS, markerSize=25, thickness=2)
            if draw_labels:
                cv2.putText(overlay, name, (data["x"], data["y"] - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
            stats["corner_markers_count"] += 1

        # 2. Overlay Personal Information Fields (Amber boxes for handwriting, Blue for bubbles)
        personal_fields = template.get("personal_fields", {})
        for field_name, field_data in personal_fields.items():
            # (a) Handwritten boxes
            hw_boxes = field_data.get("handwritten_boxes", [])
            for idx, box in enumerate(hw_boxes):
                bx, by, bw, bh = box["x"], box["y"], box["width"], box["height"]
                cv2.rectangle(overlay, (bx, by), (bx + bw, by + bh), (0, 165, 255), 2)  # Orange/Amber
                stats["handwritten_boxes_count"] += 1

            # (b) Bubble grid
            grid = field_data.get("grid", [])
            for col_bubbles in grid:
                for b in col_bubbles:
                    bcx, bcy, br = b["cx"], b["cy"], b["radius"]
                    # Draw blue circle
                    cv2.circle(overlay, (bcx, bcy), br + 2, (255, 120, 0), 1)  # Cyan/Blue
                    stats["personal_bubbles_count"] += 1

        # 3. Overlay Answer Area Bubbles (Green circles with target center)
        answer_blocks = template.get("answer_blocks", {})
        questions = answer_blocks.get("questions", {})
        stats["total_questions"] = len(questions)

        for q_num, options in questions.items():
            for opt_key, opt_data in options.items():
                acx, acy, ar = opt_data["cx"], opt_data["cy"], opt_data["radius"]
                cv2.circle(overlay, (acx, acy), ar + 2, (0, 200, 0), 2)  # Green
                cv2.circle(overlay, (acx, acy), 2, (0, 200, 0), -1)  # Center dot
                stats["answer_bubbles_count"] += 1

        # 4. Legend at bottom
        cv2.rectangle(overlay, (120, overlay.shape[0] - 65), (1480, overlay.shape[0] - 25), (240, 240, 240), -1)
        cv2.putText(overlay, "CALIBRATION OVERLAY LEGEND:  ", (140, overlay.shape[0] - 40),
                    cv2.FONT_HERSHEY_DUPLEX, 0.5, (30, 30, 30), 1)
        # Red: Markers
        cv2.rectangle(overlay, (420, overlay.shape[0] - 52), (435, overlay.shape[0] - 37), (0, 0, 255), -1)
        cv2.putText(overlay, "Corner Fiducials", (445, overlay.shape[0] - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
        # Amber: OCR
        cv2.rectangle(overlay, (610, overlay.shape[0] - 52), (625, overlay.shape[0] - 37), (0, 165, 255), -1)
        cv2.putText(overlay, "Handwriting Boxes (OCR)", (635, overlay.shape[0] - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
        # Blue: Personal bubbles
        cv2.circle(overlay, (865, overlay.shape[0] - 45), 7, (255, 120, 0), -1)
        cv2.putText(overlay, "Personal Bubbles", (880, overlay.shape[0] - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
        # Green: Answer bubbles
        cv2.circle(overlay, (1050, overlay.shape[0] - 45), 7, (0, 200, 0), -1)
        cv2.putText(overlay, "MCQ Answer Bubbles", (1065, overlay.shape[0] - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)

        return overlay, stats
