import os
import pytest
import cv2
import numpy as np
from backend.app.omr.generator import generate_standard_omr_sheet
from backend.app.omr.calibration import OMRCalibrator
from backend.app.api.v1.calibration import get_template, calibrate_default_sheet
from backend.app.models.models import User, UserRole


@pytest.fixture(scope="module")
def setup_omr_assets():
    template = generate_standard_omr_sheet("./samples/blank")
    return template


@pytest.fixture
def dummy_user():
    return User(id=1, username="test_calibrator", role=UserRole.ADMIN.value, is_active=True)


def test_generator_assets_exist(setup_omr_assets):
    assert os.path.exists("./samples/blank/omr_sheet_blank.png")
    assert os.path.exists("./samples/blank/omr_sheet_blank.pdf")
    assert os.path.exists("./samples/blank/omr_template.json")
    assert os.path.exists("./backend/app/omr/templates/standard_omr_template.json")

    img = cv2.imread("./samples/blank/omr_sheet_blank.png")
    assert img is not None
    assert img.shape[0] == 2260
    assert img.shape[1] == 1600


def test_template_structure(setup_omr_assets):
    template = setup_omr_assets
    assert "corner_markers" in template
    assert len(template["corner_markers"]) == 4

    p_fields = template["personal_fields"]
    assert "roll_no" in p_fields
    assert len(p_fields["roll_no"]["handwritten_boxes"]) == 6
    assert len(p_fields["roll_no"]["grid"]) == 6
    assert len(p_fields["roll_no"]["grid"][0]) == 10  # 0 to 9

    assert "set_code" in p_fields
    assert len(p_fields["set_code"]["grid"][0]) == 4  # A, B, C, D

    assert "name" in p_fields
    assert len(p_fields["name"]["handwritten_boxes"]) == 15
    assert len(p_fields["name"]["grid"][0]) == 26  # A to Z

    assert "mobile" in p_fields
    assert len(p_fields["mobile"]["handwritten_boxes"]) == 10

    assert "dob" in p_fields
    assert len(p_fields["dob"]["handwritten_boxes"]) == 8

    # 50 Questions
    ans_blocks = template["answer_blocks"]
    assert ans_blocks["num_questions"] == 50
    assert len(ans_blocks["questions"]) == 50
    assert "1" in ans_blocks["questions"]
    assert "50" in ans_blocks["questions"]
    assert set(ans_blocks["questions"]["1"].keys()) == {"A", "B", "C", "D"}


def test_calibrator_overlay(setup_omr_assets):
    calibrator = OMRCalibrator()
    img = cv2.imread("./samples/blank/omr_sheet_blank.png")
    overlay, stats = calibrator.overlay_calibration(img)

    assert overlay.shape == img.shape
    assert stats["corner_markers_count"] == 4
    assert stats["total_questions"] == 50
    assert stats["answer_bubbles_count"] == 200  # 50 questions * 4 options
    assert stats["handwritten_boxes_count"] > 40
    assert stats["personal_bubbles_count"] > 300


def test_calibration_api_endpoints(dummy_user):
    # 1. Test get_template
    tmpl = get_template(current_user=dummy_user)
    assert "corner_markers" in tmpl
    assert "personal_fields" in tmpl

    # 2. Test calibrate_default_sheet (JSON format)
    res_json = calibrate_default_sheet(format="json", current_user=dummy_user)
    assert res_json["status"] == "success"
    assert "stats" in res_json
    assert res_json["stats"]["answer_bubbles_count"] == 200
    assert res_json["image_data"].startswith("data:image/jpeg;base64,")

    # 3. Test calibrate_default_sheet (Image format)
    res_img = calibrate_default_sheet(format="image", current_user=dummy_user)
    assert res_img.media_type == "image/jpeg"
    assert len(res_img.body) > 1000
