"""
Synthetic OMR Dataset Generator for Accuracy Testing & Benchmark Verification.
Generates realistic filled OMR sheets with various perturbations and creates ground_truth.csv.
"""

import os
import json
import csv
import random
import numpy as np
import cv2

TEMPLATE_PATH = "samples/blank/omr_template.json"
BLANK_IMAGE_PATH = "samples/blank/omr_sheet_blank.png"
OUTPUT_DIR = "samples/filled"
GROUND_TRUTH_CSV = "samples/ground_truth.csv"


def load_template():
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def fill_bubble(img, cx, cy, radius, fill_level=0.92, smudge=False):
    """Draw a realistic shaded pencil/pen mark in a bubble."""
    # Dark graphite color with antialiasing
    fill_radius = int(radius * fill_level)
    cv2.circle(img, (int(cx), int(cy)), fill_radius, (32, 32, 32), -1, cv2.LINE_AA)
    if smudge:
        # Slight smear around the edge
        cv2.circle(img, (int(cx + 4), int(cy + 3)), int(radius * 0.4), (160, 160, 160), -1, cv2.LINE_AA)


def half_fill_bubble(img, cx, cy, radius):
    """Draw a faint/half-filled mark that falls in the UNCERTAIN range (0.30 - 0.45)."""
    # Only fill half of the circle or draw a faint scribble
    overlay = img.copy()
    cv2.ellipse(overlay, (int(cx), int(cy)), (int(radius * 0.7), int(radius * 0.4)), 30, 0, 360, (110, 110, 110), -1, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.65, img, 0.35, 0, img)


def write_handwriting(img, box, text, font_scale=0.55, thickness=2):
    """Draw realistic handwriting text inside a boxed cell."""
    x, y, w, h = box["x"], box["y"], box["width"], box["height"]
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
    tx = x + (w - tw) // 2
    ty = y + (h + th) // 2
    cv2.putText(img, text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (30, 30, 30), thickness, cv2.LINE_AA)


def fill_personal_field(img, field_template, value_str, write_boxes=True, mismatch_ocr_value=None):
    """Fills both the handwriting boxes and the bubble grid for a personal field."""
    boxes = field_template.get("handwritten_boxes", [])
    grid = field_template.get("grid", [])

    # Write in handwriting boxes
    text_for_boxes = mismatch_ocr_value if mismatch_ocr_value is not None else value_str
    if write_boxes:
        for i, ch in enumerate(text_for_boxes):
            if i < len(boxes) and ch != " ":
                write_handwriting(img, boxes[i], ch)

    # Fill bubbles in column grid
    for col_idx, ch in enumerate(value_str):
        if col_idx < len(grid):
            col_bubbles = grid[col_idx]
            for b in col_bubbles:
                if b["value"] == ch:
                    fill_bubble(img, b["cx"], b["cy"], b["radius"])
                    break


def generate_dataset():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    template = load_template()
    base_blank = cv2.imread(BLANK_IMAGE_PATH)
    if base_blank is None:
        raise FileNotFoundError(f"Blank sheet not found at {BLANK_IMAGE_PATH}")

    ground_truth_records = []

    # Standard answer patterns
    default_answers_a = {str(q): ["A", "B", "C", "D"][(q * 7 + 3) % 4] for q in range(1, 51)}
    default_answers_b = {str(q): ["B", "C", "D", "A"][(q * 11 + 5) % 4] for q in range(1, 51)}
    default_answers_c = {str(q): ["C", "D", "A", "B"][(q * 13 + 1) % 4] for q in range(1, 51)}

    questions_template = template["answer_blocks"]["questions"]

    # -------------------------------------------------------------
    # 1. Clean Perfect Sheet Set A (AUTO_ACCEPTED)
    # -------------------------------------------------------------
    img1 = base_blank.copy()
    fill_personal_field(img1, template["personal_fields"]["roll_no"], "102456")
    fill_personal_field(img1, template["personal_fields"]["name"], "RAHUL SHARMA")
    fill_personal_field(img1, template["personal_fields"]["father_name"], "SANJAY SHARMA")
    fill_personal_field(img1, template["personal_fields"]["mobile"], "9876543210")
    fill_personal_field(img1, template["personal_fields"]["set_code"], "A")
    for q, opt in default_answers_a.items():
        b = questions_template[q][opt]
        fill_bubble(img1, b["cx"], b["cy"], b["radius"])

    path1 = os.path.join(OUTPUT_DIR, "sheet_01_clean_perfect.png")
    cv2.imwrite(path1, img1)
    ground_truth_records.append({
        "filename": "sheet_01_clean_perfect.png",
        "roll_no": "102456",
        "name": "RAHUL SHARMA",
        "set_code": "A",
        "expected_status": "AUTO_ACCEPTED",
        "answers": json.dumps(default_answers_a),
        "notes": "Clean high-confidence sheet, all markers present"
    })

    # -------------------------------------------------------------
    # 2. Clean Perfect Sheet Set B (AUTO_ACCEPTED)
    # -------------------------------------------------------------
    img2 = base_blank.copy()
    fill_personal_field(img2, template["personal_fields"]["roll_no"], "203589")
    fill_personal_field(img2, template["personal_fields"]["name"], "PRIYA PATEL")
    fill_personal_field(img2, template["personal_fields"]["father_name"], "KIRAN PATEL")
    fill_personal_field(img2, template["personal_fields"]["mobile"], "9123456780")
    fill_personal_field(img2, template["personal_fields"]["set_code"], "B")
    for q, opt in default_answers_b.items():
        b = questions_template[q][opt]
        fill_bubble(img2, b["cx"], b["cy"], b["radius"])

    path2 = os.path.join(OUTPUT_DIR, "sheet_02_clean_set_b.png")
    cv2.imwrite(path2, img2)
    ground_truth_records.append({
        "filename": "sheet_02_clean_set_b.png",
        "roll_no": "203589",
        "name": "PRIYA PATEL",
        "set_code": "B",
        "expected_status": "AUTO_ACCEPTED",
        "answers": json.dumps(default_answers_b),
        "notes": "Clean Set B sheet"
    })

    # -------------------------------------------------------------
    # 3. Clean Perfect Sheet Set C (AUTO_ACCEPTED)
    # -------------------------------------------------------------
    img3 = base_blank.copy()
    fill_personal_field(img3, template["personal_fields"]["roll_no"], "304678")
    fill_personal_field(img3, template["personal_fields"]["name"], "AMIT KUMAR")
    fill_personal_field(img3, template["personal_fields"]["father_name"], "VIJAY KUMAR")
    fill_personal_field(img3, template["personal_fields"]["mobile"], "9988776655")
    fill_personal_field(img3, template["personal_fields"]["set_code"], "C")
    for q, opt in default_answers_c.items():
        b = questions_template[q][opt]
        fill_bubble(img3, b["cx"], b["cy"], b["radius"])

    path3 = os.path.join(OUTPUT_DIR, "sheet_03_clean_set_c.png")
    cv2.imwrite(path3, img3)
    ground_truth_records.append({
        "filename": "sheet_03_clean_set_c.png",
        "roll_no": "304678",
        "name": "AMIT KUMAR",
        "set_code": "C",
        "expected_status": "AUTO_ACCEPTED",
        "answers": json.dumps(default_answers_c),
        "notes": "Clean Set C sheet"
    })

    # -------------------------------------------------------------
    # 4. Rotated Sheet 2.5 degrees (AUTO_ACCEPTED after alignment)
    # -------------------------------------------------------------
    img4 = img1.copy()
    h, w = img4.shape[:2]
    M_rot = cv2.getRotationMatrix2D((w // 2, h // 2), 2.5, 1.0)
    img4_rot = cv2.warpAffine(img4, M_rot, (w, h), borderValue=(255, 255, 255))
    path4 = os.path.join(OUTPUT_DIR, "sheet_04_rotated.png")
    cv2.imwrite(path4, img4_rot)
    ground_truth_records.append({
        "filename": "sheet_04_rotated.png",
        "roll_no": "102456",
        "name": "RAHUL SHARMA",
        "set_code": "A",
        "expected_status": "AUTO_ACCEPTED",
        "answers": json.dumps(default_answers_a),
        "notes": "2.5 degree rotation corrected by fiducials"
    })

    # -------------------------------------------------------------
    # 5. Skewed / Perspective distortion (AUTO_ACCEPTED after alignment)
    # -------------------------------------------------------------
    img5 = img2.copy()
    pts1 = np.float32([[50, 50], [1500, 50], [50, 2160], [1500, 2160]])
    pts2 = np.float32([[56, 54], [1494, 48], [48, 2164], [1506, 2156]])
    M_persp = cv2.getPerspectiveTransform(pts1, pts2)
    img5_skew = cv2.warpPerspective(img5, M_persp, (w, h), borderValue=(255, 255, 255))
    path5 = os.path.join(OUTPUT_DIR, "sheet_05_skewed.png")
    cv2.imwrite(path5, img5_skew)
    ground_truth_records.append({
        "filename": "sheet_05_skewed.png",
        "roll_no": "203589",
        "name": "PRIYA PATEL",
        "set_code": "B",
        "expected_status": "AUTO_ACCEPTED",
        "answers": json.dumps(default_answers_b),
        "notes": "Perspective distortion rectified by corner markers"
    })

    # -------------------------------------------------------------
    # 6. Half-Filled / Uncertain Bubbles (NEEDS_REVIEW - strictly 0 wrong accepted!)
    # -------------------------------------------------------------
    img6 = base_blank.copy()
    fill_personal_field(img6, template["personal_fields"]["roll_no"], "405678")
    fill_personal_field(img6, template["personal_fields"]["name"], "KAVITA SINGH")
    fill_personal_field(img6, template["personal_fields"]["set_code"], "A")
    for q, opt in default_answers_a.items():
        b = questions_template[q][opt]
        if int(q) in [7, 18, 29]:
            # Half-fill / faint scribble
            half_fill_bubble(img6, b["cx"], b["cy"], b["radius"])
        else:
            fill_bubble(img6, b["cx"], b["cy"], b["radius"])

    path6 = os.path.join(OUTPUT_DIR, "sheet_06_half_filled.png")
    cv2.imwrite(path6, img6)
    ground_truth_records.append({
        "filename": "sheet_06_half_filled.png",
        "roll_no": "405678",
        "name": "KAVITA SINGH",
        "set_code": "A",
        "expected_status": "NEEDS_REVIEW",
        "answers": json.dumps(default_answers_a),
        "notes": "Questions 7, 18, 29 have faint uncertain marks"
    })

    # -------------------------------------------------------------
    # 7. Double-Marked Questions (NEEDS_REVIEW)
    # -------------------------------------------------------------
    img7 = base_blank.copy()
    fill_personal_field(img7, template["personal_fields"]["roll_no"], "506789")
    fill_personal_field(img7, template["personal_fields"]["name"], "ROHIT VERMA")
    fill_personal_field(img7, template["personal_fields"]["set_code"], "A")
    for q, opt in default_answers_a.items():
        b = questions_template[q][opt]
        fill_bubble(img7, b["cx"], b["cy"], b["radius"])
        if int(q) in [12, 34]:
            # Mark a second bubble in same question
            other_opt = "B" if opt != "B" else "C"
            b_other = questions_template[q][other_opt]
            fill_bubble(img7, b_other["cx"], b_other["cy"], b_other["radius"])

    path7 = os.path.join(OUTPUT_DIR, "sheet_07_double_marked.png")
    cv2.imwrite(path7, img7)
    ground_truth_records.append({
        "filename": "sheet_07_double_marked.png",
        "roll_no": "506789",
        "name": "ROHIT VERMA",
        "set_code": "A",
        "expected_status": "NEEDS_REVIEW",
        "answers": json.dumps(default_answers_a),
        "notes": "Questions 12, 34 double marked"
    })

    # -------------------------------------------------------------
    # 8. Name OCR Mismatch (NEEDS_REVIEW)
    # -------------------------------------------------------------
    img8 = base_blank.copy()
    fill_personal_field(img8, template["personal_fields"]["roll_no"], "607890")
    # Bubbles say "VIKRAM SINGH", but handwritten box has "RAJESH VERMA"
    fill_personal_field(img8, template["personal_fields"]["name"], "VIKRAM SINGH", mismatch_ocr_value="RAJESH VERMA")
    fill_personal_field(img8, template["personal_fields"]["set_code"], "A")
    for q, opt in default_answers_a.items():
        b = questions_template[q][opt]
        fill_bubble(img8, b["cx"], b["cy"], b["radius"])

    path8 = os.path.join(OUTPUT_DIR, "sheet_08_name_mismatch.png")
    cv2.imwrite(path8, img8)
    ground_truth_records.append({
        "filename": "sheet_08_name_mismatch.png",
        "roll_no": "607890",
        "name": "VIKRAM SINGH",
        "set_code": "A",
        "expected_status": "NEEDS_REVIEW",
        "answers": json.dumps(default_answers_a),
        "notes": "Candidate name bubbles vs OCR mismatch triggers review"
    })

    # -------------------------------------------------------------
    # 9. Blank Sheet (NEEDS_REVIEW)
    # -------------------------------------------------------------
    img9 = base_blank.copy()
    path9 = os.path.join(OUTPUT_DIR, "sheet_09_blank.png")
    cv2.imwrite(path9, img9)
    ground_truth_records.append({
        "filename": "sheet_09_blank.png",
        "roll_no": None,
        "name": None,
        "set_code": None,
        "expected_status": "NEEDS_REVIEW",
        "answers": json.dumps({}),
        "notes": "Blank sheet missing personal bubbles and answers"
    })

    # -------------------------------------------------------------
    # 10. Missing Corner Marker (NEEDS_REVIEW)
    # -------------------------------------------------------------
    img10 = img1.copy()
    # Obliterate top-right corner marker with white box
    cv2.rectangle(img10, (1480, 40), (1560, 110), (255, 255, 255), -1)
    path10 = os.path.join(OUTPUT_DIR, "sheet_10_missing_marker.png")
    cv2.imwrite(path10, img10)
    ground_truth_records.append({
        "filename": "sheet_10_missing_marker.png",
        "roll_no": "102456",
        "name": "RAHUL SHARMA",
        "set_code": "A",
        "expected_status": "NEEDS_REVIEW",
        "answers": json.dumps(default_answers_a),
        "notes": "Top right fiducial marker missing"
    })

    # -------------------------------------------------------------
    # 11. Blurred Capture (NEEDS_REVIEW)
    # -------------------------------------------------------------
    img11 = cv2.GaussianBlur(img1, (25, 25), 9.0)
    path11 = os.path.join(OUTPUT_DIR, "sheet_11_blurred.png")
    cv2.imwrite(path11, img11)
    ground_truth_records.append({
        "filename": "sheet_11_blurred.png",
        "roll_no": "102456",
        "name": "RAHUL SHARMA",
        "set_code": "A",
        "expected_status": "NEEDS_REVIEW",
        "answers": json.dumps(default_answers_a),
        "notes": "Heavy camera blur quality failure"
    })

    # -------------------------------------------------------------
    # 12. Dark Low-Light Capture (NEEDS_REVIEW)
    # -------------------------------------------------------------
    img12 = (img1.astype(np.float32) * 0.15).astype(np.uint8)
    path12 = os.path.join(OUTPUT_DIR, "sheet_12_dark.png")
    cv2.imwrite(path12, img12)
    ground_truth_records.append({
        "filename": "sheet_12_dark.png",
        "roll_no": "102456",
        "name": "RAHUL SHARMA",
        "set_code": "A",
        "expected_status": "NEEDS_REVIEW",
        "answers": json.dumps(default_answers_a),
        "notes": "Dark underexposed lighting quality failure"
    })

    # -------------------------------------------------------------
    # 13. Glare Flash Overexposure (NEEDS_REVIEW)
    # -------------------------------------------------------------
    img13 = img1.copy()
    cv2.circle(img13, (800, 800), 500, (255, 255, 255), -1)
    path13 = os.path.join(OUTPUT_DIR, "sheet_13_glare.png")
    cv2.imwrite(path13, img13)
    ground_truth_records.append({
        "filename": "sheet_13_glare.png",
        "roll_no": "102456",
        "name": "RAHUL SHARMA",
        "set_code": "A",
        "expected_status": "NEEDS_REVIEW",
        "answers": json.dumps(default_answers_a),
        "notes": "Flash glare washed out questions"
    })

    # Write Ground Truth CSV
    with open(GROUND_TRUTH_CSV, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["filename", "roll_no", "name", "set_code", "expected_status", "answers", "notes"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in ground_truth_records:
            writer.writerow(r)

    print(f"Generated {len(ground_truth_records)} test sheets in {OUTPUT_DIR}")
    print(f"Ground truth written to {GROUND_TRUTH_CSV}")


if __name__ == "__main__":
    generate_dataset()
