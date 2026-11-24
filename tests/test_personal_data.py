import os
import pytest
import cv2
import numpy as np

from backend.app.omr.bubble_engine import BubbleDecisionEngine
from backend.app.omr.decoder import PersonalDataDecoder
from backend.app.omr.ocr_engine import OCREngine
from backend.app.omr.calibration import OMRCalibrator
from backend.app.omr.engine import OMREngine


@pytest.fixture
def blank_sheet():
    img_path = "./samples/blank/omr_sheet_blank.png"
    if not os.path.exists(img_path):
        from backend.app.omr.generator import generate_standard_omr_sheet
        generate_standard_omr_sheet()
    return cv2.imread(img_path)


@pytest.fixture
def template():
    calibrator = OMRCalibrator()
    return calibrator.template


def test_digit_grid_decoder_full_valid(blank_sheet, template):
    gray = cv2.cvtColor(blank_sheet, cv2.COLOR_BGR2GRAY)
    roll_config = template["personal_fields"]["roll_no"]

    # Fill roll number bubbles for digits: 1 0 2 3 4 5
    digits = [1, 0, 2, 3, 4, 5]
    marked_sheet = gray.copy()
    for col_idx, d in enumerate(digits):
        bubble = roll_config["grid"][col_idx][d]
        cv2.circle(marked_sheet, (bubble["cx"], bubble["cy"]), bubble["radius"] - 2, 20, -1)

    decoder = PersonalDataDecoder()
    res = decoder.decode_field(marked_sheet, "roll_no", roll_config)
    assert res["value"] == "102345"
    assert res["is_uncertain"] is False
    assert len(res["uncertain_reasons"]) == 0


def test_digit_grid_decoder_blank_column(blank_sheet, template):
    gray = cv2.cvtColor(blank_sheet, cv2.COLOR_BGR2GRAY)
    roll_config = template["personal_fields"]["roll_no"]

    # Fill only 5 digits, leave 6th column blank
    digits = [1, 0, 2, 3, 4]
    marked_sheet = gray.copy()
    for col_idx, d in enumerate(digits):
        bubble = roll_config["grid"][col_idx][d]
        cv2.circle(marked_sheet, (bubble["cx"], bubble["cy"]), bubble["radius"] - 2, 20, -1)

    decoder = PersonalDataDecoder()
    res = decoder.decode_field(marked_sheet, "roll_no", roll_config)
    assert res["is_uncertain"] is True
    assert any("blank" in r.lower() for r in res["uncertain_reasons"])


def test_digit_grid_decoder_multi_marked_column(blank_sheet, template):
    gray = cv2.cvtColor(blank_sheet, cv2.COLOR_BGR2GRAY)
    roll_config = template["personal_fields"]["roll_no"]

    marked_sheet = gray.copy()
    # Fill col 0 with digit 1 AND digit 8
    b1 = roll_config["grid"][0][1]
    b8 = roll_config["grid"][0][8]
    cv2.circle(marked_sheet, (b1["cx"], b1["cy"]), b1["radius"] - 2, 20, -1)
    cv2.circle(marked_sheet, (b8["cx"], b8["cy"]), b8["radius"] - 2, 20, -1)

    decoder = PersonalDataDecoder()
    res = decoder.decode_field(marked_sheet, "roll_no", roll_config)
    assert res["is_uncertain"] is True
    assert any("multiple" in r.lower() for r in res["uncertain_reasons"])


def test_ocr_engine_similarity_calculation():
    # Exact match
    assert OCREngine.calculate_similarity("RAHUL SHARMA", "RAHUL SHARMA") == 1.0
    assert OCREngine.calculate_similarity("102345", "102345") == 1.0

    # Minor typo / OCR discrepancy (1 letter different)
    sim_minor = OCREngine.calculate_similarity("RAHUL SHARMA", "RAHUL SHAPMA")
    assert sim_minor > 0.85

    # Completely different names
    sim_diff = OCREngine.calculate_similarity("RAHUL SHARMA", "AMIT VERMA")
    assert sim_diff < 0.50


def test_ocr_handwriting_box_crop(blank_sheet, template):
    ocr = OCREngine()
    name_boxes = template["personal_fields"]["name"]["handwritten_boxes"]

    crop, b64 = ocr.crop_field_boxes(blank_sheet, name_boxes)
    assert crop is not None
    assert crop.shape[0] > 0
    assert crop.shape[1] > 0
    assert b64.startswith("data:image/jpeg;base64,")


def test_ocr_synthetic_handwriting_recognition():
    ocr = OCREngine()

    # Create a synthetic white canvas with crisp black text "102345"
    canvas_digits = np.full((60, 200, 3), 255, dtype=np.uint8)
    cv2.putText(canvas_digits, "102345", (20, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)

    text_digits = ocr.recognize_text(canvas_digits, allow_digits_only=True)
    assert text_digits == "102345"

    # Create a synthetic white canvas with text "RAHUL SHARMA"
    canvas_letters = np.full((60, 360, 3), 255, dtype=np.uint8)
    cv2.putText(canvas_letters, "RAHUL SHARMA", (15, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)

    text_letters = ocr.recognize_text(canvas_letters, allow_letters_only=True)
    assert "RAHUL" in text_letters and "SHARMA" in text_letters


def test_end_to_end_personal_data_pipeline(blank_sheet, template):
    # Mark roll number 998877 and Set Code A
    marked = blank_sheet.copy()
    roll_config = template["personal_fields"]["roll_no"]
    digits = [9, 9, 8, 8, 7, 7]
    for col_idx, d in enumerate(digits):
        b = roll_config["grid"][col_idx][d]
        cv2.circle(marked, (b["cx"], b["cy"]), b["radius"] - 2, (20, 20, 20), -1)

    set_config = template["personal_fields"]["set_code"]
    b_set_a = set_config["grid"][0][0]  # Option A
    cv2.circle(marked, (b_set_a["cx"], b_set_a["cy"]), b_set_a["radius"] - 2, (20, 20, 20), -1)

    # Write handwritten roll number in the boxes
    boxes = roll_config["handwritten_boxes"]
    for idx, d in enumerate(digits):
        bx = boxes[idx]["x"]
        by = boxes[idx]["y"]
        cv2.putText(marked, str(d), (bx + 6, by + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

    engine = OMREngine()
    res = engine.process_image(marked, run_ocr=True)

    assert res["success"] is True
    assert res["student_data"]["roll_no"]["bubble_value"] == "998877"
    assert res["student_data"]["set_code"]["bubble_value"] == "A"
    assert res["student_data"]["roll_no"]["is_uncertain"] is False
    assert res["student_data"]["roll_no"]["crop_image_base64"].startswith("data:image/jpeg;base64,")
