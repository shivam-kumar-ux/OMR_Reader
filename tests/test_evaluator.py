import pytest
from backend.app.omr.evaluator import EvaluationEngine
from backend.app.omr.validator import AccuracyValidator
from backend.app.models.models import MultiMarkedRule, SheetStatus, User, UserRole, Student, Exam, Result
from backend.app.db.session import SessionLocal


def test_evaluator_all_correct():
    engine = EvaluationEngine(marks_per_correct=4.0, negative_marks=1.0)
    answer_keys = {i: "A" for i in range(1, 51)}
    student_answers = {i: {"marked_option": "A", "status": "SINGLE", "confidence": 0.99} for i in range(1, 51)}

    res = engine.evaluate_sheet(student_answers, answer_keys, total_questions=50)
    assert res["correct_count"] == 50
    assert res["wrong_count"] == 0
    assert res["not_attempted_count"] == 0
    assert res["total_score"] == 200.0
    assert res["percentage"] == 100.0


def test_evaluator_negative_marking_and_unattempted():
    engine = EvaluationEngine(marks_per_correct=4.0, negative_marks=1.0)
    answer_keys = {1: "A", 2: "B", 3: "C", 4: "D"}
    student_answers = {
        1: {"marked_option": "A", "status": "SINGLE"},      # Correct: +4
        2: {"marked_option": "C", "status": "SINGLE"},      # Wrong: -1
        3: {"marked_option": None, "status": "EMPTY"},      # Unattempted: 0
        4: {"marked_option": "D", "status": "SINGLE"},      # Correct: +4
    }

    res = engine.evaluate_sheet(student_answers, answer_keys, total_questions=4)
    assert res["correct_count"] == 2
    assert res["wrong_count"] == 1
    assert res["not_attempted_count"] == 1
    # 4 - 1 + 0 + 4 = 7
    assert res["total_score"] == 7.0


def test_evaluator_multi_marked_rules():
    # Rule 1: COUNT_AS_WRONG
    engine_wrong = EvaluationEngine(marks_per_correct=4.0, negative_marks=1.0, multi_marked_rule=MultiMarkedRule.COUNT_AS_WRONG.value)
    answer_keys = {1: "A"}
    student_answers = {1: {"marked_option": "AB", "status": "MULTI"}}
    res_wrong = engine_wrong.evaluate_sheet(student_answers, answer_keys, total_questions=1)
    assert res_wrong["multi_marked_count"] == 1
    assert res_wrong["wrong_count"] == 1
    assert res_wrong["total_score"] == -1.0

    # Rule 2: COUNT_AS_NOT_ATTEMPTED
    engine_na = EvaluationEngine(marks_per_correct=4.0, negative_marks=1.0, multi_marked_rule=MultiMarkedRule.COUNT_AS_NOT_ATTEMPTED.value)
    res_na = engine_na.evaluate_sheet(student_answers, answer_keys, total_questions=1)
    assert res_na["multi_marked_count"] == 1
    assert res_na["wrong_count"] == 0
    assert res_na["total_score"] == 0.0


def test_validator_auto_accepted():
    engine_output = {
        "success": True,
        "aligned_image": "mock_img",
        "review_reasons": [],
        "student_data": {
            "roll_no": {"bubble_value": "100234", "is_uncertain": False},
            "set_code": {"bubble_value": "A", "is_uncertain": False},
            "name": {"bubble_value": "RAHUL SHARMA", "ocr_value": "RAHUL SHARMA", "similarity_score": 1.0},
        },
        "answers": {1: {"status": "SINGLE", "marked_option": "B"}},
        "summary": {"uncertain_count": 0},
    }

    status, reasons, rois = AccuracyValidator.validate_for_acceptance(engine_output, exam_id=1)
    assert status == SheetStatus.AUTO_ACCEPTED.value
    assert len(reasons) == 0
    assert len(rois) == 0


def test_validator_uncertain_question_flags_needs_review():
    engine_output = {
        "success": True,
        "aligned_image": "mock_img",
        "review_reasons": ["Question 5 bubble is uncertain"],
        "student_data": {
            "roll_no": {"bubble_value": "100234", "is_uncertain": False},
            "set_code": {"bubble_value": "A", "is_uncertain": False},
            "name": {"bubble_value": "RAHUL SHARMA", "ocr_value": "RAHUL SHARMA", "similarity_score": 1.0},
        },
        "answers": {5: {"status": "UNCERTAIN"}},
        "summary": {"uncertain_count": 1},
    }

    status, reasons, rois = AccuracyValidator.validate_for_acceptance(engine_output, exam_id=1)
    assert status == SheetStatus.NEEDS_REVIEW.value
    assert any("uncertain" in r.lower() for r in reasons)
    assert any(roi.get("question_no") == 5 for roi in rois)


def test_validator_ocr_name_mismatch_flags_needs_review():
    engine_output = {
        "success": True,
        "aligned_image": "mock_img",
        "review_reasons": [],
        "student_data": {
            "roll_no": {"bubble_value": "100234", "is_uncertain": False},
            "set_code": {"bubble_value": "B", "is_uncertain": False},
            # Bubbles say RAHUL SHARMA, handwriting OCR says AMIT VERMA
            "name": {"bubble_value": "RAHUL SHARMA", "ocr_value": "AMIT VERMA", "similarity_score": 0.35},
        },
        "answers": {},
        "summary": {"uncertain_count": 0},
    }

    status, reasons, rois = AccuracyValidator.validate_for_acceptance(
        engine_output, exam_id=1, name_similarity_threshold=0.75
    )
    assert status == SheetStatus.NEEDS_REVIEW.value
    assert any("similarity" in r.lower() for r in reasons)
    assert any(roi.get("type") == "ocr_mismatch" for roi in rois)


def test_validator_duplicate_roll_number():
    db = SessionLocal()
    try:
        # Create exam & student
        exam = db.query(Exam).first()
        if not exam:
            exam = Exam(
                name="Validation Exam",
                code="VAL-01",
                total_questions=50,
                sets_config=["A"],
                correct_mark=1.0,
                negative_mark=0.0
            )
            db.add(exam)
            db.commit()
            db.refresh(exam)
        assert exam is not None

        # Clean student with roll "888777"
        old_s = db.query(Student).filter(Student.roll_no == "888777").first()
        if old_s:
            db.query(Result).filter(Result.student_id == old_s.id).delete()
            db.delete(old_s)
            db.commit()

        student = Student(roll_no="888777", name_final="EXISTING STUDENT")
        db.add(student)
        db.commit()
        db.refresh(student)

        res = Result(student_id=student.id, exam_id=exam.id, total_score=50.0)
        db.add(res)
        db.commit()

        engine_output = {
            "success": True,
            "aligned_image": "mock_img",
            "review_reasons": [],
            "student_data": {
                "roll_no": {"bubble_value": "888777", "is_uncertain": False},
                "set_code": {"bubble_value": "A", "is_uncertain": False},
                "name": {"bubble_value": "SAME STUDENT", "ocr_value": "SAME STUDENT", "similarity_score": 1.0},
            },
            "answers": {},
            "summary": {"uncertain_count": 0},
        }

        status, reasons, rois = AccuracyValidator.validate_for_acceptance(
            engine_output, exam_id=exam.id, db=db
        )
        assert status == SheetStatus.NEEDS_REVIEW.value
        assert any("duplicate" in r.lower() for r in reasons)
    finally:
        db.close()
