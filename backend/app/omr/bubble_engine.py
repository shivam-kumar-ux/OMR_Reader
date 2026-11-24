from typing import Dict, Any, Tuple, List, Optional
import cv2
import numpy as np


class BubbleState:
    FILLED = "FILLED"
    EMPTY = "EMPTY"
    UNCERTAIN = "UNCERTAIN"


class QuestionState:
    SINGLE = "SINGLE"
    EMPTY = "EMPTY"
    MULTI = "MULTI"
    UNCERTAIN = "UNCERTAIN"


class BubbleDecisionEngine:
    """
    Adaptive thresholding and bubble classifier.
    Computes fill ratios relative to local background paper intensity
    and classifies bubbles and questions.
    """

    def __init__(
        self,
        fill_threshold: float = 0.45,
        uncertain_low: float = 0.30,
        uncertain_high: float = 0.45,
    ):
        self.fill_threshold = fill_threshold
        self.uncertain_low = uncertain_low
        self.uncertain_high = uncertain_high

    def analyze_bubble(
        self,
        gray_image: np.ndarray,
        cx: int,
        cy: int,
        radius: int,
    ) -> Dict[str, Any]:
        """
        Analyzes a single bubble circle on the grayscale image.
        Returns fill ratio, contrast, background luminance, and classification.
        """
        h, w = gray_image.shape[:2]
        r = int(radius)
        # Ensure coordinates within image bounds
        if cx - r - 6 < 0 or cx + r + 6 >= w or cy - r - 6 < 0 or cy + r + 6 >= h:
            return {
                "cx": cx,
                "cy": cy,
                "radius": r,
                "fill_ratio": 0.0,
                "bg_mean": 255.0,
                "contrast": 0.0,
                "state": BubbleState.UNCERTAIN,
            }

        # 1. Sample surrounding background ring (annulus from r+2 to r+6)
        outer_mask = np.zeros((2 * r + 14, 2 * r + 14), dtype=np.uint8)
        inner_mask = np.zeros((2 * r + 14, 2 * r + 14), dtype=np.uint8)
        center_sub = (r + 7, r + 7)

        cv2.circle(outer_mask, center_sub, r + 6, 255, -1)
        cv2.circle(inner_mask, center_sub, r + 2, 255, -1)
        annulus_mask = cv2.bitwise_and(outer_mask, cv2.bitwise_not(inner_mask))

        sub_img = gray_image[cy - r - 7 : cy + r + 7, cx - r - 7 : cx + r + 7]
        bg_pixels = sub_img[annulus_mask > 0]
        bg_mean = float(np.mean(bg_pixels)) if len(bg_pixels) > 0 else 240.0

        # 2. Sample bubble interior (shrink radius slightly by 1-2 px to avoid circle border)
        interior_mask = np.zeros(sub_img.shape, dtype=np.uint8)
        cv2.circle(interior_mask, center_sub, max(r - 2, 3), 255, -1)

        interior_pixels = sub_img[interior_mask > 0]
        total_interior_px = len(interior_pixels)
        if total_interior_px == 0:
            return {
                "cx": cx,
                "cy": cy,
                "radius": r,
                "fill_ratio": 0.0,
                "bg_mean": bg_mean,
                "contrast": 0.0,
                "state": BubbleState.UNCERTAIN,
            }

        interior_mean = float(np.mean(interior_pixels))

        # Pixel threshold for darkness: at least 32 levels darker than local background
        dark_threshold = max(bg_mean - 32.0, 40.0)
        dark_pixels_count = np.count_nonzero(interior_pixels < dark_threshold)
        fill_ratio = float(dark_pixels_count / total_interior_px)

        contrast = float((bg_mean - interior_mean) / max(bg_mean, 1.0))

        # Classification based on fill ratio AND contrast with background paper
        if fill_ratio >= self.fill_threshold and contrast >= 0.28:
            state = BubbleState.FILLED
        elif fill_ratio <= self.uncertain_low or contrast <= 0.16:
            state = BubbleState.EMPTY
        else:
            state = BubbleState.UNCERTAIN

        return {
            "cx": cx,
            "cy": cy,
            "radius": r,
            "fill_ratio": round(fill_ratio, 4),
            "bg_mean": round(bg_mean, 1),
            "contrast": round(contrast, 4),
            "state": state,
        }

    def evaluate_question(
        self,
        gray_image: np.ndarray,
        question_no: int,
        options_dict: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Evaluates a multiple-choice question by analyzing all its option bubbles.
        Returns:
            marked_option: str (e.g. "A", "B", None if empty, "AB" if multi)
            status: SINGLE, EMPTY, MULTI, UNCERTAIN
            confidence: float (0.0 to 1.0)
            bubble_results: dict of per-option analysis
        """
        bubble_results = {}
        filled_options = []
        uncertain_options = []

        for opt_key, opt_data in options_dict.items():
            analysis = self.analyze_bubble(
                gray_image,
                opt_data["cx"],
                opt_data["cy"],
                opt_data["radius"],
            )
            bubble_results[opt_key] = analysis
            if analysis["state"] == BubbleState.FILLED:
                filled_options.append((opt_key, analysis["fill_ratio"]))
            elif analysis["state"] == BubbleState.UNCERTAIN:
                uncertain_options.append((opt_key, analysis["fill_ratio"]))

        # Sort filled options by fill ratio descending
        filled_options.sort(key=lambda x: x[1], reverse=True)

        # Decision Logic:
        # Case 1: Any bubble is in UNCERTAIN range (and not clearly overridden by a 90%+ filled bubble)
        if uncertain_options:
            # If there's an overwhelming winner (e.g. A has 85% fill and B has 20% faint erasure)
            if len(filled_options) == 1 and filled_options[0][1] >= 0.75:
                # Strong fill dominates a very faint mark
                status = QuestionState.SINGLE
                marked_option = filled_options[0][0]
                confidence = 0.88
            else:
                status = QuestionState.UNCERTAIN
                marked_option = uncertain_options[0][0]
                confidence = 0.50

        # Case 2: No uncertain bubbles
        elif len(filled_options) == 0:
            status = QuestionState.EMPTY
            marked_option = None
            confidence = 1.0

        elif len(filled_options) == 1:
            status = QuestionState.SINGLE
            marked_option = filled_options[0][0]
            # Higher confidence if fill ratio is crisp and gap to runner-up is large
            ratios = [b["fill_ratio"] for b in bubble_results.values()]
            ratios.sort(reverse=True)
            gap = ratios[0] - ratios[1] if len(ratios) > 1 else ratios[0]
            confidence = min(0.70 + 0.30 * min(gap * 2, 1.0), 0.99)

        else:
            # Multi-marked
            status = QuestionState.MULTI
            marked_option = "".join(sorted([opt for opt, _ in filled_options]))
            confidence = 0.85

        return {
            "question_no": question_no,
            "marked_option": marked_option,
            "status": status,
            "confidence": round(confidence, 4),
            "bubbles": bubble_results,
        }
