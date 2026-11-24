from typing import Dict, Any, List, Tuple, Optional
import numpy as np
from backend.app.omr.bubble_engine import BubbleDecisionEngine, BubbleState


class PersonalDataDecoder:
    """
    Decodes personal information bubble grids (digits 0-9 and letters A-Z).
    Enforces the strict rule:
    'A column that is blank, multi-marked, or uncertain makes that field uncertain.'
    """

    def __init__(self, bubble_engine: Optional[BubbleDecisionEngine] = None):
        self.bubble_engine = bubble_engine or BubbleDecisionEngine()

    def decode_field(
        self,
        gray_image: np.ndarray,
        field_name: str,
        field_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Decodes a multi-column bubble grid.
        Returns:
            decoded_value: str
            raw_columns: list of column character choices
            is_uncertain: bool
            uncertain_reasons: list of str
            confidence: float (0.0 - 1.0)
        """
        grid = field_config.get("grid", [])
        field_type = field_config.get("type", "digits")
        num_columns = field_config.get("num_columns", len(grid))

        col_chars = []
        col_statuses = []
        uncertain_reasons = []
        confidences = []

        for col_idx, col_bubbles in enumerate(grid):
            filled_opts = []
            uncertain_opts = []

            for b in col_bubbles:
                analysis = self.bubble_engine.analyze_bubble(
                    gray_image, b["cx"], b["cy"], b["radius"]
                )
                if analysis["state"] == BubbleState.FILLED:
                    filled_opts.append((b["value"], analysis["fill_ratio"]))
                elif analysis["state"] == BubbleState.UNCERTAIN:
                    uncertain_opts.append((b["value"], analysis["fill_ratio"]))

            # If one bubble is strongly filled (e.g. >= 0.70), it dominates faint smudges
            if len(filled_opts) == 1 and filled_opts[0][1] >= 0.70:
                col_chars.append(filled_opts[0][0])
                col_statuses.append("SINGLE")
                confidences.append(0.98)

            elif uncertain_opts:
                col_chars.append("?")
                col_statuses.append("UNCERTAIN")
                uncertain_reasons.append(f"{field_name} col {col_idx+1}: bubble is uncertain")
                confidences.append(0.5)

            elif len(filled_opts) == 0:
                col_chars.append(" ")
                col_statuses.append("EMPTY")
                confidences.append(1.0)

            elif len(filled_opts) == 1:
                col_chars.append(filled_opts[0][0])
                col_statuses.append("SINGLE")
                confidences.append(0.98)

            else:
                # Multi-marked
                col_chars.append("X")
                col_statuses.append("MULTI")
                opts_str = "".join([o for o, _ in filled_opts])
                uncertain_reasons.append(f"{field_name} col {col_idx+1}: multiple bubbles shaded ({opts_str})")
                confidences.append(0.70)

        raw_str = "".join(col_chars)
        trimmed_str = raw_str.rstrip()

        # Evaluation of uncertainty per field type:
        is_uncertain = False

        if field_name == "roll_no":
            # Roll number must have every digit decoded cleanly
            if " " in raw_str or "?" in raw_str or "X" in raw_str or len(trimmed_str) != num_columns:
                is_uncertain = True
                if " " in raw_str:
                    uncertain_reasons.append("Roll number contains blank columns")

        elif field_name == "set_code":
            # Set code must be single non-empty letter (A, B, C, D)
            if trimmed_str not in {"A", "B", "C", "D"}:
                is_uncertain = True
                if not trimmed_str:
                    uncertain_reasons.append("Set code bubble is empty")

        elif field_name == "name":
            # Name can end with blanks, but cannot contain '?' or 'X'
            if "?" in trimmed_str or "X" in trimmed_str:
                is_uncertain = True
            if not trimmed_str:
                is_uncertain = True
                uncertain_reasons.append("Candidate name bubbles are completely empty")

        elif field_name in {"mobile", "dob", "class_name"}:
            if "?" in trimmed_str or "X" in trimmed_str:
                is_uncertain = True
            # If partially filled
            if field_name == "mobile" and trimmed_str and len(trimmed_str) < 10:
                is_uncertain = True
                uncertain_reasons.append(f"Mobile number has only {len(trimmed_str)} digits")
            if field_name == "dob" and trimmed_str and len(trimmed_str) < 8:
                is_uncertain = True
                uncertain_reasons.append(f"DOB has only {len(trimmed_str)} digits")

        avg_conf = float(np.mean(confidences)) if confidences else 1.0

        return {
            "field_name": field_name,
            "value": trimmed_str,
            "raw_value": raw_str,
            "is_uncertain": is_uncertain,
            "uncertain_reasons": uncertain_reasons,
            "confidence": round(avg_conf, 4),
            "column_statuses": col_statuses,
        }

    def decode_all_personal_fields(
        self,
        gray_image: np.ndarray,
        personal_fields_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Decodes all personal information fields defined in template.
        """
        results = {}
        for field_name, config in personal_fields_config.items():
            if config.get("type") == "handwritten_only" or not config.get("grid"):
                continue
            results[field_name] = self.decode_field(gray_image, field_name, config)
        return results
