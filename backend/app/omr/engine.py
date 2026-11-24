import os
from typing import Dict, Any, Tuple, Optional, List
import cv2
import numpy as np

from backend.app.omr.preprocessor import ImagePreprocessor, QualityCheckResult
from backend.app.omr.aligner import SheetAligner
from backend.app.omr.bubble_engine import BubbleDecisionEngine, QuestionState
from backend.app.omr.calibration import OMRCalibrator


class OMREngine:
    """
    Core pipeline orchestrating:
    - Preprocessing & Quality Checks
    - Corner Marker Detection & Perspective Alignment
    - Bubble Classification & Question Evaluation
    - Processed debug visualization generation
    """

    def __init__(
        self,
        template_path: str = "./backend/app/omr/templates/standard_omr_template.json",
        fill_threshold: float = 0.45,
        uncertain_low: float = 0.24,
        uncertain_high: float = 0.45,
    ):
        self.calibrator = OMRCalibrator(template_path)
        self.template = self.calibrator.template
        self.aligner = SheetAligner()
        self.bubble_engine = BubbleDecisionEngine(
            fill_threshold=fill_threshold,
            uncertain_low=uncertain_low,
            uncertain_high=uncertain_high,
        )

    def process_image(
        self,
        image: np.ndarray,
        strict_quality: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes complete OMR pipeline on an input image.
        Returns detailed extraction results and diagnostic metadata.
        """
        output: Dict[str, Any] = {
            "success": False,
            "status": "NEEDS_REVIEW",
            "review_reasons": [],
            "quality_metrics": {},
            "aligned_image": None,
            "processed_image": None,
            "answers": {},
            "summary": {
                "total_questions": 0,
                "single_count": 0,
                "empty_count": 0,
                "multi_count": 0,
                "uncertain_count": 0,
            },
        }

        # Step 1: Quality Check
        quality = ImagePreprocessor.check_image_quality(image)
        output["quality_metrics"] = quality.metrics
        if strict_quality and not quality.passed:
            output["review_reasons"].append(quality.reason)
            return output

        # Step 2: Marker Detection & Perspective Alignment
        success, aligned, align_err, marker_coords = self.aligner.detect_markers_and_align(
            image, self.template
        )
        if not success:
            output["review_reasons"].append(f"Marker alignment failed: {align_err}")
            return output

        output["aligned_image"] = aligned

        # Step 3: Question Bubble Evaluation
        if len(aligned.shape) == 3:
            gray_aligned = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
        else:
            gray_aligned = aligned

        questions_dict = self.template.get("answer_blocks", {}).get("questions", {})
        output["summary"]["total_questions"] = len(questions_dict)

        answers_result = {}
        processed_viz = aligned.copy()
        if len(processed_viz.shape) == 2:
            processed_viz = cv2.cvtColor(processed_viz, cv2.COLOR_GRAY2BGR)

        for q_str, options in questions_dict.items():
            q_no = int(q_str)
            eval_res = self.bubble_engine.evaluate_question(gray_aligned, q_no, options)
            answers_result[q_no] = eval_res

            # Update summary counts
            st = eval_res["status"]
            if st == QuestionState.SINGLE:
                output["summary"]["single_count"] += 1
            elif st == QuestionState.EMPTY:
                output["summary"]["empty_count"] += 1
            elif st == QuestionState.MULTI:
                output["summary"]["multi_count"] += 1
                output["review_reasons"].append(f"Question {q_no} is multi-marked ({eval_res['marked_option']})")
            elif st == QuestionState.UNCERTAIN:
                output["summary"]["uncertain_count"] += 1
                output["review_reasons"].append(f"Question {q_no} marked bubble is uncertain")

            # Draw visual feedback on processed debug image
            for opt_key, opt_data in options.items():
                cx, cy, r = opt_data["cx"], opt_data["cy"], opt_data["radius"]
                b_info = eval_res["bubbles"].get(opt_key, {})
                b_state = b_info.get("state")

                if b_state == "FILLED":
                    if st == QuestionState.SINGLE:
                        # Green solid circle for valid single answer
                        cv2.circle(processed_viz, (cx, cy), r + 2, (0, 220, 0), 2)
                        cv2.circle(processed_viz, (cx, cy), 3, (0, 220, 0), -1)
                    else:
                        # Red circle for multi-marked bubble
                        cv2.circle(processed_viz, (cx, cy), r + 2, (0, 0, 255), 2)
                elif b_state == "UNCERTAIN":
                    # Amber/Yellow circle for uncertain bubble
                    cv2.circle(processed_viz, (cx, cy), r + 2, (0, 180, 255), 2)
                else:
                    # Faint grey ring for empty
                    cv2.circle(processed_viz, (cx, cy), r, (180, 180, 180), 1)

        output["answers"] = answers_result
        output["processed_image"] = processed_viz

        if output["summary"]["uncertain_count"] == 0 and len(output["review_reasons"]) == 0:
            output["status"] = "AUTO_ACCEPTED"
            output["success"] = True
        else:
            output["status"] = "NEEDS_REVIEW"
            output["success"] = True  # Image processed, requires review

        return output
