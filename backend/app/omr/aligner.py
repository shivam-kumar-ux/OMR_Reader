from typing import Dict, Any, Tuple, Optional
import cv2
import numpy as np


class SheetAligner:
    """
    Detects the four fiducial corner markers on an OMR sheet and applies
    perspective transformation to align the sheet to standard template dimensions.
    """

    def __init__(self, target_width: int = 1600, target_height: int = 2260):
        self.target_width = target_width
        self.target_height = target_height

        # Standard destination points matching template corner centers:
        # top-left: (75, 75), top-right: (1525, 75), bottom-right: (1525, 2185), bottom-left: (75, 2185)
        self.dst_pts = np.float32([
            [75, 75],        # Top-Left
            [1525, 75],      # Top-Right
            [1525, 2185],    # Bottom-Right
            [75, 2185],      # Bottom-Left
        ])

    def detect_markers_and_align(
        self,
        image: np.ndarray,
        template: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[np.ndarray], str, Dict[str, Any]]:
        """
        Attempts to detect all 4 corner markers.
        Returns:
            (success, warped_image, error_message, detected_marker_centers)
        """
        if image is None or image.size == 0:
            return False, None, "Invalid image data", {}

        h, w = image.shape[:2]
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Preprocessing for marker extraction
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 10
        )

        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # Expected corner regions (within 18% of width and 15% of height from each corner)
        corner_search_margin_x = w * 0.18
        corner_search_margin_y = h * 0.15

        quadrants = {
            "top_left": {
                "x_range": (0, corner_search_margin_x),
                "y_range": (0, corner_search_margin_y),
                "candidate": None,
                "score": -1,
            },
            "top_right": {
                "x_range": (w - corner_search_margin_x, w),
                "y_range": (0, corner_search_margin_y),
                "candidate": None,
                "score": -1,
            },
            "bottom_left": {
                "x_range": (0, corner_search_margin_x),
                "y_range": (h - corner_search_margin_y, h),
                "candidate": None,
                "score": -1,
            },
            "bottom_right": {
                "x_range": (w - corner_search_margin_x, w),
                "y_range": (h - corner_search_margin_y, h),
                "candidate": None,
                "score": -1,
            },
        }

        min_area = (w * h) * 0.0002   # approx 700 px
        max_area = (w * h) * 0.015    # approx 54000 px

        for c in contours:
            area = cv2.contourArea(c)
            if area < min_area or area > max_area:
                continue

            x, y, cw, ch = cv2.boundingRect(c)
            aspect_ratio = float(cw) / float(ch) if ch > 0 else 0
            if aspect_ratio < 0.70 or aspect_ratio > 1.40:
                continue

            rect_area = cw * ch
            extent = float(area) / rect_area if rect_area > 0 else 0
            if extent < 0.65:  # Fiducial square marker is solid
                continue

            M = cv2.moments(c)
            if M["m00"] == 0:
                continue
            cx = float(M["m10"] / M["m00"])
            cy = float(M["m01"] / M["m00"])

            for q_name, q_info in quadrants.items():
                min_x, max_x = q_info["x_range"]
                min_y, max_y = q_info["y_range"]
                if min_x <= cx <= max_x and min_y <= cy <= max_y:
                    score = area * extent * (1.0 - abs(1.0 - aspect_ratio))
                    if score > q_info["score"]:
                        q_info["score"] = score
                        q_info["candidate"] = (cx, cy)

        # Check if any corner marker is missing
        missing_markers = []
        for q_name, q_info in quadrants.items():
            if q_info["candidate"] is None:
                missing_markers.append(q_name.replace("_", " "))

        if missing_markers:
            return (
                False,
                None,
                f"Missing corner marker: {', '.join(missing_markers)}",
                {k: v["candidate"] for k, v in quadrants.items()},
            )

        tl = quadrants["top_left"]["candidate"]
        tr = quadrants["top_right"]["candidate"]
        br = quadrants["bottom_right"]["candidate"]
        bl = quadrants["bottom_left"]["candidate"]

        src_pts = np.float32([tl, tr, br, bl])

        if template and "corner_markers" in template:
            tm = template["corner_markers"]
            dst_pts = np.float32([
                tm["top_left"]["center"],
                tm["top_right"]["center"],
                tm["bottom_right"]["center"],
                tm["bottom_left"]["center"],
            ])
        else:
            dst_pts = self.dst_pts

        matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped = cv2.warpPerspective(
            image, matrix, (self.target_width, self.target_height), flags=cv2.INTER_LANCZOS4
        )

        detected_coords = {
            "top_left": tl,
            "top_right": tr,
            "bottom_right": br,
            "bottom_left": bl,
        }

        return True, warped, "", detected_coords
