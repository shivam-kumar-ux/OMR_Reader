"""
Automated Accuracy & Benchmark Test Suite for OMR Engine.
Ingests benchmark filled sheets, measures bubble & personal data accuracy,
and strictly asserts that 0 wrong fields are ever auto-accepted.
"""

import os
import json
import csv
import pytest
import cv2
import numpy as np

from backend.app.omr.engine import OMREngine
from backend.app.omr.validator import AccuracyValidator
from backend.app.db.session import SessionLocal
from backend.app.models.models import Exam

GROUND_TRUTH_CSV = "samples/ground_truth.csv"
FILLED_DIR = "samples/filled"


def run_benchmark():
    engine = OMREngine()
    validator = AccuracyValidator()

    db = SessionLocal()
    # Ensure a reference exam exists
    exam = db.query(Exam).first()
    if not exam:
        exam = Exam(
            name="Benchmark Exam",
            code="BENCH-01",
            total_questions=50,
            marks_per_correct=1.0,
            negative_marks=0.0
        )
        db.add(exam)
        db.commit()
        db.refresh(exam)
    exam_id = exam.id
    db.close()

    with open(GROUND_TRUTH_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = list(reader)

    total_sheets = len(records)
    auto_accepted_count = 0
    needs_review_count = 0
    wrong_auto_accepted_fields = 0

    total_bubbles = 0
    correct_bubbles = 0

    total_personal_fields = 0
    correct_personal_fields = 0

    results_summary = []

    for r in records:
        filename = r["filename"]
        img_path = os.path.join(FILLED_DIR, filename)
        img = cv2.imread(img_path)
        assert img is not None, f"Failed to load image {img_path}"

        expected_status = r["expected_status"]
        expected_roll = r["roll_no"]
        expected_name = r["name"]
        expected_set = r["set_code"]
        expected_answers = json.loads(r["answers"]) if r["answers"] else {}

        # Run OMR Engine
        engine_res = engine.process_image(img)

        # Run Accuracy Validator with strict 0-defect policy
        db = SessionLocal()
        try:
            status, reasons, rois = validator.validate_for_acceptance(
                engine_output=engine_res,
                exam_id=exam_id,
                db=db
            )
        finally:
            db.close()

        is_auto_accepted = (status == "AUTO_ACCEPTED")
        if is_auto_accepted:
            auto_accepted_count += 1
        else:
            needs_review_count += 1

        personal_data = engine_res.get("student_data", {})
        extracted_roll = personal_data.get("roll_no", {}).get("bubble_value")
        extracted_name = personal_data.get("name", {}).get("bubble_value")
        extracted_set = personal_data.get("set_code", {}).get("bubble_value")
        extracted_answers = engine_res.get("answers", {})

        # Compare answers accuracy
        sheet_wrong_fields = 0
        if expected_answers:
            for q_str, exp_opt in expected_answers.items():
                total_bubbles += 4  # 4 choices evaluated
                ans_obj = extracted_answers.get(int(q_str), {})
                marked_opt = ans_obj.get("marked_option")
                if marked_opt == exp_opt:
                    correct_bubbles += 4
                else:
                    if is_auto_accepted:
                        sheet_wrong_fields += 1

        # Compare personal data accuracy
        if expected_roll:
            total_personal_fields += 1
            if extracted_roll == expected_roll:
                correct_personal_fields += 1
            elif is_auto_accepted:
                sheet_wrong_fields += 1

        if expected_name:
            total_personal_fields += 1
            if extracted_name == expected_name:
                correct_personal_fields += 1
            elif is_auto_accepted:
                sheet_wrong_fields += 1

        if expected_set:
            total_personal_fields += 1
            if extracted_set == expected_set:
                correct_personal_fields += 1
            elif is_auto_accepted:
                sheet_wrong_fields += 1

        if is_auto_accepted and sheet_wrong_fields > 0:
            wrong_auto_accepted_fields += sheet_wrong_fields

        results_summary.append({
            "filename": filename,
            "expected_status": expected_status,
            "actual_status": status,
            "reasons": reasons,
            "wrong_fields_in_sheet": sheet_wrong_fields,
            "notes": r["notes"]
        })

    bubble_acc = (correct_bubbles / total_bubbles * 100) if total_bubbles > 0 else 0.0
    personal_acc = (correct_personal_fields / total_personal_fields * 100) if total_personal_fields > 0 else 0.0

    return {
        "total_sheets": total_sheets,
        "auto_accepted_count": auto_accepted_count,
        "needs_review_count": needs_review_count,
        "wrong_auto_accepted_fields": wrong_auto_accepted_fields,
        "bubble_accuracy": bubble_acc,
        "personal_accuracy": personal_acc,
        "details": results_summary
    }


def test_accuracy_benchmark():
    """
    Main accuracy test asserting 0 wrong values among auto-accepted sheets.
    """
    stats = run_benchmark()

    print("\n" + "=" * 80)
    print("           OMR ACCURACY & DEFECT AUDIT BENCHMARK REPORT")
    print("=" * 80)
    print(f"Total Sheets Evaluated:         {stats['total_sheets']}")
    print(f"Auto-Accepted Sheets:           {stats['auto_accepted_count']}")
    print(f"Sheets Sent to Review:          {stats['needs_review_count']}")
    print(f"Bubble Classification Accuracy: {stats['bubble_accuracy']:.2f}%")
    print(f"Personal Data Accuracy:         {stats['personal_accuracy']:.2f}%")
    print("-" * 80)
    print(f">>> WRONG VALUES AMONG AUTO-ACCEPTED: {stats['wrong_auto_accepted_fields']} <<<")
    print("=" * 80)

    for item in stats["details"]:
        match_symbol = "✓" if item["actual_status"] == item["expected_status"] else "✗"
        print(f"[{match_symbol}] {item['filename']:<30} Expected: {item['expected_status']:<14} Actual: {item['actual_status']:<14}")
        if item["reasons"]:
            print(f"    Reason: {item['reasons']}")

    print("=" * 80 + "\n")

    # Strict accuracy requirement from prompt:
    # "Target: 0 wrong values among auto-accepted sheets."
    assert stats["wrong_auto_accepted_fields"] == 0, (
        f"CRITICAL DEFECT: Found {stats['wrong_auto_accepted_fields']} wrong values in AUTO_ACCEPTED sheets!"
    )

    # Ensure clean sheets were accepted and perturbed/degraded sheets were sent to review
    assert stats["auto_accepted_count"] >= 3, "Expected clean benchmark sheets to be auto-accepted"
    assert stats["needs_review_count"] >= 5, "Expected degraded/uncertain sheets to be sent to review"


if __name__ == "__main__":
    test_accuracy_benchmark()
