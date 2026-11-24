import os
import pytest
import cv2
import numpy as np
from backend.app.omr.preprocessor import ImagePreprocessor
from backend.app.omr.aligner import SheetAligner
from backend.app.omr.bubble_engine import BubbleDecisionEngine, BubbleState, QuestionState
from backend.app.omr.engine import OMREngine


@pytest.fixture
def blank_sheet():
    img_path = "./samples/blank/omr_sheet_blank.png"
    if not os.path.exists(img_path):
        from backend.app.omr.generator import generate_standard_omr_sheet
        generate_standard_omr_sheet()
    img = cv2.imread(img_path)
    return img


def test_quality_check_clean_sheet(blank_sheet):
    res = ImagePreprocessor.check_image_quality(blank_sheet)
    assert res.passed is True
    assert res.metrics["mean_luminance"] > 200
    assert res.metrics["blur_variance"] > 100


def test_quality_check_blurry_image(blank_sheet):
    # Simulate heavy blur
    blurred = cv2.GaussianBlur(blank_sheet, (35, 35), 0)
    res = ImagePreprocessor.check_image_quality(blurred)
    assert res.passed is False
    assert "blurry" in res.reason.lower()


def test_quality_check_dark_image(blank_sheet):
    # Simulate very dark scan
    dark = (blank_sheet * 0.15).astype(np.uint8)
    res = ImagePreprocessor.check_image_quality(dark)
    assert res.passed is False
    assert "dark" in res.reason.lower()


def test_quality_check_glare_image(blank_sheet):
    # Simulate glare / overexposure
    glare = blank_sheet.copy()
    glare[:, :] = 255
    res = ImagePreprocessor.check_image_quality(glare)
    assert res.passed is False
    assert "glare" in res.reason.lower()


def test_corner_marker_detection_and_alignment(blank_sheet):
    aligner = SheetAligner()
    success, aligned, err, coords = aligner.detect_markers_and_align(blank_sheet)
    assert success is True
    assert aligned is not None
    assert aligned.shape[0] == 2260
    assert aligned.shape[1] == 1600
    assert len(coords) == 4


def test_missing_corner_marker(blank_sheet):
    # Erase top-right marker
    corrupted = blank_sheet.copy()
    corrupted[0:200, 1400:1600] = 255  # White out top-right

    aligner = SheetAligner()
    success, aligned, err, coords = aligner.detect_markers_and_align(corrupted)
    assert success is False
    assert "missing corner marker" in err.lower()
    assert "top right" in err.lower()


def test_rotated_and_skewed_sheet(blank_sheet):
    # Apply 2-degree rotation and slight translation
    h, w = blank_sheet.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), 2.5, 0.98)
    rotated = cv2.warpAffine(blank_sheet, M, (w, h), borderValue=(255, 255, 255))

    aligner = SheetAligner()
    success, aligned, err, coords = aligner.detect_markers_and_align(rotated)
    assert success is True
    assert aligned.shape == (2260, 1600, 3)


def test_bubble_engine_states(blank_sheet):
    gray = cv2.cvtColor(blank_sheet, cv2.COLOR_BGR2GRAY)
    engine = OMREngine()
    template = engine.template

    q1_options = template["answer_blocks"]["questions"]["1"]
    opt_a = q1_options["A"]

    # 1. On blank sheet, bubble is EMPTY
    res_empty = engine.bubble_engine.analyze_bubble(gray, opt_a["cx"], opt_a["cy"], opt_a["radius"])
    assert res_empty["state"] == BubbleState.EMPTY
    assert res_empty["fill_ratio"] < 0.22

    # 2. Fill option A with black circle
    marked_sheet = gray.copy()
    cv2.circle(marked_sheet, (opt_a["cx"], opt_a["cy"]), opt_a["radius"] - 2, 20, -1)

    res_filled = engine.bubble_engine.analyze_bubble(marked_sheet, opt_a["cx"], opt_a["cy"], opt_a["radius"])
    assert res_filled["state"] == BubbleState.FILLED
    assert res_filled["fill_ratio"] > 0.60

    # 3. Evaluate entire question
    q_eval = engine.bubble_engine.evaluate_question(marked_sheet, 1, q1_options)
    assert q_eval["status"] == QuestionState.SINGLE
    assert q_eval["marked_option"] == "A"


def test_multi_marked_and_uncertain_question(blank_sheet):
    gray = cv2.cvtColor(blank_sheet, cv2.COLOR_BGR2GRAY)
    engine = OMREngine()
    q2_options = engine.template["answer_blocks"]["questions"]["2"]

    # Multi-marked: Fill both B and C
    multi_sheet = gray.copy()
    cv2.circle(multi_sheet, (q2_options["B"]["cx"], q2_options["B"]["cy"]), q2_options["B"]["radius"] - 2, 20, -1)
    cv2.circle(multi_sheet, (q2_options["C"]["cx"], q2_options["C"]["cy"]), q2_options["C"]["radius"] - 2, 20, -1)

    q_multi = engine.bubble_engine.evaluate_question(multi_sheet, 2, q2_options)
    assert q_multi["status"] == QuestionState.MULTI
    assert "B" in q_multi["marked_option"] and "C" in q_multi["marked_option"]

    # Uncertain / faint smudge: fill with light gray
    faint_sheet = gray.copy()
    # Light smudge filling only ~25% of pixels
    cv2.circle(faint_sheet, (q2_options["A"]["cx"], q2_options["A"]["cy"]), 4, 80, -1)
    q_uncertain = engine.bubble_engine.evaluate_question(faint_sheet, 2, q2_options)
    assert q_uncertain["status"] in {QuestionState.UNCERTAIN, QuestionState.EMPTY}


def test_full_engine_on_blank_sheet(blank_sheet):
    engine = OMREngine()
    res = engine.process_image(blank_sheet)
    assert res["success"] is True
    assert res["summary"]["total_questions"] == 50
    assert res["summary"]["empty_count"] == 50
    assert res["summary"]["single_count"] == 0
    assert res["summary"]["uncertain_count"] == 0
    assert res["processed_image"] is not None
