import os
from typing import Dict, Any, Tuple, Optional, List
import cv2
import numpy as np

from backend.app.core.config import settings
from backend.app.omr.preprocessor import ImagePreprocessor, QualityCheckResult
from backend.app.omr.aligner import SheetAligner
from backend.app.omr.bubble_engine import BubbleDecisionEngine, QuestionState
from backend.app.omr.calibration import OMRCalibrator
from backend.app.omr.decoder import PersonalDataDecoder
from backend.app.omr.ocr_engine import OCREngine


class OMREngine:
    """
    Core end-to-end pipeline orchestrating:
    - Preprocessing & Quality Checks
    - Corner Marker Detection & Perspective Alignment
    - Personal Information Bubble Decoding (digits 0-9 & letters A-Z)
    - Handwriting Crop & OCR Cross-Check (RapidOCR)
    - Multiple-Choice Bubble Evaluation (Adaptive thresholding)
    - Strict Auto-Acceptance vs Needs-Review decision logic
    - Processed diagnostic visualization generation
    """

    def __init__(
        self,
        template_path: str = "./backend/app/omr/templates/standard_omr_template.json",
        fill_threshold: float = None,
        uncertain_low: float = None,
        uncertain_high: float = None,
        ocr_similarity_threshold: float = None,
    ):
        self.calibrator = OMRCalibrator(template_path)
        self.template = self.calibrator.template
        self.aligner = SheetAligner()

        ft = fill_threshold if fill_threshold is not None else settings.BUBBLE_FILL_THRESHOLD
        ul = uncertain_low if uncertain_low is not None else settings.BUBBLE_UNCERTAIN_LOW
        uh = uncertain_high if uncertain_high is not None else settings.BUBBLE_UNCERTAIN_HIGH

        self.bubble_engine = BubbleDecisionEngine(
            fill_threshold=ft,
            uncertain_low=ul,
            uncertain_high=uh,
        )
        self.decoder = PersonalDataDecoder(self.bubble_engine)
        self.ocr_engine = OCREngine()
        self.ocr_similarity_threshold = (
            ocr_similarity_threshold
            if ocr_similarity_threshold is not None
            else settings.OCR_NAME_SIMILARITY_THRESHOLD
        )

    def process_image(
        self,
        image: np.ndarray,
        run_ocr: bool = True,
        strict_quality: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes complete OMR pipeline on an input image.
        Returns:
            {
               "success": bool,
               "status": "AUTO_ACCEPTED" | "NEEDS_REVIEW",
               "review_reasons": list of str,
               "quality_metrics": dict,
               "aligned_image": ndarray,
               "processed_image": ndarray,
               "student_data": dict,
               "answers": dict,
               "summary": dict,
               "confidence_score": float
            }
        """
        output: Dict[str, Any] = {
            "success": False,
            "status": "NEEDS_REVIEW",
            "review_reasons": [],
            "quality_metrics": {},
            "aligned_image": None,
            "processed_image": None,
            "student_data": {},
            "answers": {},
            "summary": {
                "total_questions": 0,
                "single_count": 0,
                "empty_count": 0,
                "multi_count": 0,
                "uncertain_count": 0,
            },
            "confidence_score": 1.0,
        }

        # Step 1: Quality Check
        quality = ImagePreprocessor.check_image_quality(image)
        output["quality_metrics"] = quality.metrics
        if strict_quality and not quality.passed:
            output["review_reasons"].append(quality.reason)
            output["confidence_score"] = 0.30
            return output

        # Step 2: Marker Detection & Perspective Alignment
        success, aligned, align_err, marker_coords = self.aligner.detect_markers_and_align(
            image, self.template
        )
        if not success:
            output["review_reasons"].append(f"Marker alignment failed: {align_err}")
            output["confidence_score"] = 0.20
            return output

        output["aligned_image"] = aligned

        if len(aligned.shape) == 3:
            gray_aligned = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
        else:
            gray_aligned = aligned.copy()

        # Step 3: Decode Personal Information Bubble Grids
        personal_config = self.template.get("personal_fields", {})
        decoded_fields = self.decoder.decode_all_personal_fields(gray_aligned, personal_config)

        # Step 4: Handwriting Crops & OCR Cross-Check
        student_data: Dict[str, Any] = {}
        personal_confidences = []

        for field_name, config in personal_config.items():
            field_decode = decoded_fields.get(field_name, {})
            bubble_val = field_decode.get("value", "")
            is_uncertain = field_decode.get("is_uncertain", False)

            if is_uncertain:
                for reason in field_decode.get("uncertain_reasons", []):
                    output["review_reasons"].append(reason)

            personal_confidences.append(field_decode.get("confidence", 0.9))

            # Run OCR cross-check if enabled
            if run_ocr:
                ocr_res = self.ocr_engine.cross_check_field(
                    aligned,
                    field_name,
                    config,
                    bubble_val,
                    similarity_threshold=self.ocr_similarity_threshold,
                )
                if not ocr_res["match_passed"]:
                    output["review_reasons"].append(ocr_res["reason"])

                ocr_val = ocr_res["ocr_value"]
                sim_score = ocr_res["similarity_score"]
                crop_b64 = ocr_res["crop_image_base64"]
            else:
                ocr_val = ""
                sim_score = 1.0
                crop_b64 = ""

            student_data[field_name] = {
                "bubble_value": bubble_val,
                "ocr_value": ocr_val,
                "final_value": bubble_val if bubble_val else ocr_val,
                "similarity_score": sim_score,
                "is_uncertain": is_uncertain,
                "crop_image_base64": crop_b64,
            }

        # Handle Father's Name (handwritten only box)
        if "father_name" in personal_config:
            fn_config = personal_config["father_name"]
            if run_ocr:
                fn_crop, fn_b64 = self.ocr_engine.crop_field_boxes(aligned, fn_config.get("handwritten_boxes", []))
                fn_ocr = self.ocr_engine.recognize_text(fn_crop, allow_letters_only=True)
            else:
                fn_ocr, fn_b64 = "", ""
            student_data["father_name"] = {
                "bubble_value": "",
                "ocr_value": fn_ocr,
                "final_value": fn_ocr,
                "similarity_score": 1.0,
                "is_uncertain": False,
                "crop_image_base64": fn_b64,
            }

        output["student_data"] = student_data

        # Enforce rule: Roll number must be fully decoded
        roll_info = student_data.get("roll_no", {})
        if not roll_info.get("bubble_value") or roll_info.get("is_uncertain"):
            if "Roll number is not fully decoded" not in output["review_reasons"]:
                output["review_reasons"].append("Roll number is not fully decoded from bubbles")

        # Step 5: Question Bubble Evaluation
        questions_dict = self.template.get("answer_blocks", {}).get("questions", {})
        output["summary"]["total_questions"] = len(questions_dict)

        answers_result = {}
        question_confidences = []

        processed_viz = aligned.copy()
        if len(processed_viz.shape) == 2:
            processed_viz = cv2.cvtColor(processed_viz, cv2.COLOR_GRAY2BGR)

        for q_str, options in questions_dict.items():
            q_no = int(q_str)
            eval_res = self.bubble_engine.evaluate_question(gray_aligned, q_no, options)
            answers_result[q_no] = eval_res
            question_confidences.append(eval_res["confidence"])

            st = eval_res["status"]
            if st == QuestionState.SINGLE:
                output["summary"]["single_count"] += 1
            elif st == QuestionState.EMPTY:
                output["summary"]["empty_count"] += 1
            elif st == QuestionState.MULTI:
                output["summary"]["multi_count"] += 1
                output["review_reasons"].append(f"Q{q_no} is multi-marked ({eval_res['marked_option']})")
            elif st == QuestionState.UNCERTAIN:
                output["summary"]["uncertain_count"] += 1
                output["review_reasons"].append(f"Q{q_no} bubble is uncertain")

            # Draw visual markers on processed image
            for opt_key, opt_data in options.items():
                cx, cy, r = opt_data["cx"], opt_data["cy"], opt_data["radius"]
                b_info = eval_res["bubbles"].get(opt_key, {})
                b_state = b_info.get("state")

                if b_state == "FILLED":
                    if st == QuestionState.SINGLE:
                        cv2.circle(processed_viz, (cx, cy), r + 2, (0, 220, 0), 2)
                        cv2.circle(processed_viz, (cx, cy), 3, (0, 220, 0), -1)
                    else:
                        cv2.circle(processed_viz, (cx, cy), r + 2, (0, 0, 255), 2)
                elif b_state == "UNCERTAIN":
                    cv2.circle(processed_viz, (cx, cy), r + 2, (0, 180, 255), 2)
                else:
                    cv2.circle(processed_viz, (cx, cy), r, (180, 180, 180), 1)

        output["answers"] = answers_result
        output["processed_image"] = processed_viz

        # Step 6: Compute Overall Confidence Score
        all_confs = personal_confidences + question_confidences
        raw_conf = float(np.mean(all_confs)) if all_confs else 1.0

        if output["review_reasons"]:
            # Reduce confidence score based on number of issues
            penalty = len(output["review_reasons"]) * 0.08
            output["confidence_score"] = round(max(raw_conf - penalty, 0.20), 4)
            output["status"] = "NEEDS_REVIEW"
            output["success"] = True
        else:
            output["confidence_score"] = round(raw_conf, 4)
            output["status"] = "AUTO_ACCEPTED"
            output["success"] = True

        return output
