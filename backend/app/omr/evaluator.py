from typing import Dict, Any, List, Optional
from backend.app.models.models import MultiMarkedRule, SheetStatus


class EvaluationEngine:
    """
    Evaluates decoded student answers against stored answer keys.
    Computes scores, negative marking, question status, and accuracy metrics.
    """

    def __init__(
        self,
        marks_per_correct: float = 4.0,
        negative_marks: float = 1.0,
        multi_marked_rule: str = MultiMarkedRule.COUNT_AS_WRONG.value,
    ):
        self.marks_per_correct = marks_per_correct
        self.negative_marks = negative_marks
        self.multi_marked_rule = multi_marked_rule

    def evaluate_sheet(
        self,
        decoded_answers: Dict[int, Dict[str, Any]],
        answer_keys: Dict[int, str],
        total_questions: int = 50,
    ) -> Dict[str, Any]:
        """
        Evaluates student marked answers against answer key.
        Returns:
            {
               "total_questions": int,
               "correct_count": int,
               "wrong_count": int,
               "not_attempted_count": int,
               "multi_marked_count": int,
               "uncertain_count": int,
               "total_score": float,
               "max_marks": float,
               "percentage": float,
               "question_evaluations": list
            }
        """
        correct_count = 0
        wrong_count = 0
        not_attempted_count = 0
        multi_marked_count = 0
        uncertain_count = 0
        total_score = 0.0

        evaluations = []

        for q_no in range(1, total_questions + 1):
            ans_info = decoded_answers.get(q_no, {})
            marked_option = ans_info.get("marked_option")
            status = ans_info.get("status", "EMPTY")
            confidence = ans_info.get("confidence", 1.0)
            correct_option = answer_keys.get(q_no)

            is_correct = None
            marks_delta = 0.0

            if status == "UNCERTAIN":
                uncertain_count += 1
                # Uncertain questions do not award or deduct marks until verified
                is_correct = None
                marks_delta = 0.0

            elif status == "EMPTY" or not marked_option:
                not_attempted_count += 1
                is_correct = None
                marks_delta = 0.0

            elif status == "MULTI" or len(marked_option) > 1:
                multi_marked_count += 1
                if self.multi_marked_rule == MultiMarkedRule.COUNT_AS_WRONG.value:
                    wrong_count += 1
                    is_correct = False
                    marks_delta = -self.negative_marks
                else:
                    # COUNT_AS_NOT_ATTEMPTED
                    is_correct = None
                    marks_delta = 0.0

            else:
                # Single marked option
                if correct_option and marked_option == correct_option:
                    correct_count += 1
                    is_correct = True
                    marks_delta = self.marks_per_correct
                else:
                    wrong_count += 1
                    is_correct = False
                    marks_delta = -self.negative_marks

            total_score += marks_delta

            evaluations.append({
                "question_no": q_no,
                "marked_option": marked_option,
                "correct_option": correct_option,
                "is_correct": is_correct,
                "status": status,
                "confidence": confidence,
                "marks_awarded": marks_delta,
            })

        max_marks = total_questions * self.marks_per_correct
        percentage = round((total_score / max_marks) * 100.0, 2) if max_marks > 0 else 0.0

        return {
            "total_questions": total_questions,
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "not_attempted_count": not_attempted_count,
            "multi_marked_count": multi_marked_count,
            "uncertain_count": uncertain_count,
            "total_score": round(total_score, 2),
            "max_marks": round(max_marks, 2),
            "percentage": max(percentage, 0.0),
            "question_evaluations": evaluations,
        }
