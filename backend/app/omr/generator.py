import json
import os
from typing import Dict, Any
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def generate_standard_omr_sheet(output_dir: str = "./samples/blank") -> Dict[str, Any]:
    """
    Generates a standard canonical A4 OMR sheet image and template JSON.
    Width: 1600 px, Height: 2260 px.
    Includes:
    - 4 corner fiducial markers for perspective correction
    - Student personal details:
        * Roll No (6 digits, handwritten boxes + 0-9 bubble grid)
        * Set Code (A, B, C, D, handwritten box + bubbles)
        * Name (15 letters, handwritten boxes + A-Z bubble grid)
        * Mobile (10 digits, handwritten boxes + 0-9 bubble grid)
        * DOB (8 digits, handwritten boxes + 0-9 bubble grid)
        * Class (2 digits, handwritten boxes + 0-9 bubble grid)
    - 50 MCQ questions (2 columns of 25 questions, options A, B, C, D)
    """
    os.makedirs(output_dir, exist_ok=True)
    width = 1600
    height = 2260

    # Create white canvas
    img = np.full((height, width, 3), 255, dtype=np.uint8)

    template: Dict[str, Any] = {
        "page_dimensions": {"width": width, "height": height},
        "corner_markers": {},
        "personal_fields": {},
        "answer_blocks": {},
    }

    marker_size = 50
    margin_x = 50
    margin_y = 50

    # 1. Corner Fiducials
    # Top-Left
    tl = (margin_x, margin_y)
    # Top-Right
    tr = (width - margin_x - marker_size, margin_y)
    # Bottom-Left
    bl = (margin_x, height - margin_y - marker_size)
    # Bottom-Right
    br = (width - margin_x - marker_size, height - margin_y - marker_size)

    corners = [("top_left", tl), ("top_right", tr), ("bottom_left", bl), ("bottom_right", br)]
    for name, (cx, cy) in corners:
        # Draw solid black square with inner white border and center black dot
        cv2.rectangle(img, (cx, cy), (cx + marker_size, cy + marker_size), (0, 0, 0), -1)
        template["corner_markers"][name] = {
            "x": cx,
            "y": cy,
            "width": marker_size,
            "height": marker_size,
            "center": [cx + marker_size // 2, cy + marker_size // 2],
        }

    # Outer decorative alignment boundary line
    cv2.rectangle(img, (margin_x + marker_size + 15, margin_y + marker_size + 15),
                  (width - margin_x - marker_size - 15, height - margin_y - marker_size - 15),
                  (40, 40, 40), 2)

    # 2. Header
    header_y = 90
    cv2.putText(img, "OMR EXAMINATION & EVALUATION SYSTEM", (280, header_y),
                cv2.FONT_HERSHEY_DUPLEX, 1.1, (20, 20, 20), 2, cv2.LINE_AA)
    cv2.putText(img, "INSTRUCTIONS: Use Black/Blue ballpoint pen. Fill bubbles completely like (X). Darken only one circle per question.",
                (200, header_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (70, 70, 70), 1, cv2.LINE_AA)

    # Convert to PIL for crisp text drawing if needed, or use OpenCV font
    # 3. Personal Fields Section (Y ~ 160 to 1100)
    # Section Header
    cv2.rectangle(img, (120, 150), (1480, 185), (230, 230, 230), -1)
    cv2.putText(img, "STUDENT PERSONAL INFORMATION (WRITE IN BOXES & SHADE BUBBLES BELOW)",
                (260, 175), cv2.FONT_HERSHEY_DUPLEX, 0.65, (30, 30, 30), 2, cv2.LINE_AA)

    # (A) Roll Number (6 cols, digits 0-9)
    # Position: X: 120, Y: 200
    roll_x = 120
    roll_y = 200
    col_w = 28
    box_h = 32
    bubble_r = 9
    bubble_gap_y = 24

    cv2.putText(img, "ROLL NUMBER", (roll_x + 5, roll_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    roll_boxes_y = roll_y + 10

    template["personal_fields"]["roll_no"] = {
        "type": "digits",
        "num_columns": 6,
        "handwritten_boxes": [],
        "grid": [],
    }

    for col in range(6):
        bx = roll_x + col * col_w
        cv2.rectangle(img, (bx, roll_boxes_y), (bx + col_w, roll_boxes_y + box_h), (0, 0, 0), 2)
        template["personal_fields"]["roll_no"]["handwritten_boxes"].append({
            "x": bx, "y": roll_boxes_y, "width": col_w, "height": box_h
        })

        col_bubbles = []
        grid_start_y = roll_boxes_y + box_h + 15
        for d in range(10):
            by = grid_start_y + d * bubble_gap_y
            cx = bx + col_w // 2
            cy = by + bubble_r
            cv2.circle(img, (cx, cy), bubble_r, (0, 0, 0), 2)
            cv2.putText(img, str(d), (cx - 4, cy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80, 80, 80), 1)
            col_bubbles.append({"value": str(d), "cx": cx, "cy": cy, "radius": bubble_r})
        template["personal_fields"]["roll_no"]["grid"].append(col_bubbles)

    # (B) Set Code (1 col, A, B, C, D)
    set_x = 320
    cv2.putText(img, "SET", (set_x + 5, roll_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.rectangle(img, (set_x, roll_boxes_y), (set_x + col_w, roll_boxes_y + box_h), (0, 0, 0), 2)

    template["personal_fields"]["set_code"] = {
        "type": "letters",
        "num_columns": 1,
        "handwritten_boxes": [{"x": set_x, "y": roll_boxes_y, "width": col_w, "height": box_h}],
        "grid": [],
    }
    set_bubbles = []
    set_options = ["A", "B", "C", "D"]
    for idx, opt in enumerate(set_options):
        by = roll_boxes_y + box_h + 15 + idx * bubble_gap_y
        cx = set_x + col_w // 2
        cy = by + bubble_r
        cv2.circle(img, (cx, cy), bubble_r, (0, 0, 0), 2)
        cv2.putText(img, opt, (cx - 4, cy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80, 80, 80), 1)
        set_bubbles.append({"value": opt, "cx": cx, "cy": cy, "radius": bubble_r})
    template["personal_fields"]["set_code"]["grid"].append(set_bubbles)

    # (C) Class (2 cols, 0-9)
    class_x = 380
    cv2.putText(img, "CLASS", (class_x + 2, roll_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    template["personal_fields"]["class_name"] = {
        "type": "digits",
        "num_columns": 2,
        "handwritten_boxes": [],
        "grid": [],
    }
    for col in range(2):
        bx = class_x + col * col_w
        cv2.rectangle(img, (bx, roll_boxes_y), (bx + col_w, roll_boxes_y + box_h), (0, 0, 0), 2)
        template["personal_fields"]["class_name"]["handwritten_boxes"].append({
            "x": bx, "y": roll_boxes_y, "width": col_w, "height": box_h
        })
        col_bubbles = []
        for d in range(10):
            by = roll_boxes_y + box_h + 15 + d * bubble_gap_y
            cx = bx + col_w // 2
            cy = by + bubble_r
            cv2.circle(img, (cx, cy), bubble_r, (0, 0, 0), 2)
            cv2.putText(img, str(d), (cx - 4, cy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80, 80, 80), 1)
            col_bubbles.append({"value": str(d), "cx": cx, "cy": cy, "radius": bubble_r})
        template["personal_fields"]["class_name"]["grid"].append(col_bubbles)

    # (D) Mobile Number (10 cols, digits 0-9)
    mob_x = 470
    cv2.putText(img, "MOBILE NUMBER", (mob_x + 50, roll_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    template["personal_fields"]["mobile"] = {
        "type": "digits",
        "num_columns": 10,
        "handwritten_boxes": [],
        "grid": [],
    }
    for col in range(10):
        bx = mob_x + col * col_w
        cv2.rectangle(img, (bx, roll_boxes_y), (bx + col_w, roll_boxes_y + box_h), (0, 0, 0), 2)
        template["personal_fields"]["mobile"]["handwritten_boxes"].append({
            "x": bx, "y": roll_boxes_y, "width": col_w, "height": box_h
        })
        col_bubbles = []
        for d in range(10):
            by = roll_boxes_y + box_h + 15 + d * bubble_gap_y
            cx = bx + col_w // 2
            cy = by + bubble_r
            cv2.circle(img, (cx, cy), bubble_r, (0, 0, 0), 2)
            cv2.putText(img, str(d), (cx - 4, cy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80, 80, 80), 1)
            col_bubbles.append({"value": str(d), "cx": cx, "cy": cy, "radius": bubble_r})
        template["personal_fields"]["mobile"]["grid"].append(col_bubbles)

    # (E) Date of Birth (8 cols: DDMMYYYY)
    dob_x = 780
    cv2.putText(img, "DATE OF BIRTH (DDMMYYYY)", (dob_x + 10, roll_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    template["personal_fields"]["dob"] = {
        "type": "digits",
        "num_columns": 8,
        "handwritten_boxes": [],
        "grid": [],
    }
    for col in range(8):
        bx = dob_x + col * col_w
        cv2.rectangle(img, (bx, roll_boxes_y), (bx + col_w, roll_boxes_y + box_h), (0, 0, 0), 2)
        template["personal_fields"]["dob"]["handwritten_boxes"].append({
            "x": bx, "y": roll_boxes_y, "width": col_w, "height": box_h
        })
        col_bubbles = []
        for d in range(10):
            by = roll_boxes_y + box_h + 15 + d * bubble_gap_y
            cx = bx + col_w // 2
            cy = by + bubble_r
            cv2.circle(img, (cx, cy), bubble_r, (0, 0, 0), 2)
            cv2.putText(img, str(d), (cx - 4, cy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80, 80, 80), 1)
            col_bubbles.append({"value": str(d), "cx": cx, "cy": cy, "radius": bubble_r})
        template["personal_fields"]["dob"]["grid"].append(col_bubbles)

    # (F) Candidate Name (15 cols, letters A-Z)
    name_x = 1040
    name_col_w = 26
    cv2.putText(img, "CANDIDATE FULL NAME", (name_x + 60, roll_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    template["personal_fields"]["name"] = {
        "type": "letters",
        "num_columns": 15,
        "handwritten_boxes": [],
        "grid": [],
    }
    letters = [chr(i) for i in range(ord('A'), ord('Z') + 1)]
    letter_gap_y = 21
    letter_bubble_r = 8

    for col in range(15):
        bx = name_x + col * name_col_w
        cv2.rectangle(img, (bx, roll_boxes_y), (bx + name_col_w, roll_boxes_y + box_h), (0, 0, 0), 2)
        template["personal_fields"]["name"]["handwritten_boxes"].append({
            "x": bx, "y": roll_boxes_y, "width": name_col_w, "height": box_h
        })
        col_bubbles = []
        for l_idx, letter in enumerate(letters):
            by = roll_boxes_y + box_h + 12 + l_idx * letter_gap_y
            cx = bx + name_col_w // 2
            cy = by + letter_bubble_r
            cv2.circle(img, (cx, cy), letter_bubble_r, (0, 0, 0), 1)
            cv2.putText(img, letter, (cx - 4, cy + 3), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (100, 100, 100), 1)
            col_bubbles.append({"value": letter, "cx": cx, "cy": cy, "radius": letter_bubble_r})
        template["personal_fields"]["name"]["grid"].append(col_bubbles)

    # (G) Father's Name (15 handwritten boxes, Y ~ 530)
    father_y = 530
    cv2.putText(img, "FATHER'S FULL NAME (HANDWRITTEN)", (120, father_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    father_boxes_y = father_y + 10
    template["personal_fields"]["father_name"] = {
        "type": "handwritten_only",
        "num_columns": 15,
        "handwritten_boxes": [],
        "grid": [],
    }
    father_col_w = 40
    for col in range(15):
        bx = 120 + col * father_col_w
        cv2.rectangle(img, (bx, father_boxes_y), (bx + father_col_w, father_boxes_y + 40), (0, 0, 0), 2)
        template["personal_fields"]["father_name"]["handwritten_boxes"].append({
            "x": bx, "y": father_boxes_y, "width": father_col_w, "height": 40
        })

    # Separator Line between Personal Info and Answer Area
    sep_y = 810
    cv2.line(img, (100, sep_y), (1500, sep_y), (0, 0, 0), 2)

    # 4. Answers Section Header
    ans_header_y = sep_y + 35
    cv2.rectangle(img, (120, sep_y + 10), (1480, sep_y + 45), (230, 230, 230), -1)
    cv2.putText(img, "ANSWERS SECTION (MULTIPLE CHOICE QUESTIONS - 50 QUESTIONS)",
                (340, ans_header_y), cv2.FONT_HERSHEY_DUPLEX, 0.7, (20, 20, 20), 2, cv2.LINE_AA)

    # 50 Questions in 2 Columns:
    # Column 1: Questions 1 to 25 (X: 180 to 760)
    # Column 2: Questions 26 to 50 (X: 840 to 1420)
    ans_start_y = sep_y + 70
    ans_gap_y = 38
    ans_bubble_r = 11
    ans_opt_gap_x = 46

    template["answer_blocks"] = {
        "num_questions": 50,
        "questions": {},
    }

    col1_x = 220
    col2_x = 880

    for i in range(1, 51):
        if i <= 25:
            # Column 1
            row_idx = i - 1
            base_x = col1_x
            base_y = ans_start_y + row_idx * ans_gap_y
        else:
            # Column 2
            row_idx = i - 26
            base_x = col2_x
            base_y = ans_start_y + row_idx * ans_gap_y

        # Draw Question number
        q_label = f"Q{i:02d}"
        cv2.putText(img, q_label, (base_x - 70, base_y + 6), cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 0, 0), 2)

        # Bubble coordinates for options A, B, C, D
        q_bubbles = {}
        for opt_idx, opt in enumerate(["A", "B", "C", "D"]):
            cx = base_x + opt_idx * ans_opt_gap_x
            cy = base_y
            cv2.circle(img, (cx, cy), ans_bubble_r, (0, 0, 0), 2)
            cv2.putText(img, opt, (cx - 5, cy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (60, 60, 60), 1)
            q_bubbles[opt] = {"cx": cx, "cy": cy, "radius": ans_bubble_r}

        # Light divider line after every 5 questions
        if i % 5 == 0 and (i != 25 and i != 50):
            cv2.line(img, (base_x - 80, base_y + 18), (base_x + 180, base_y + 18), (200, 200, 200), 1)

        template["answer_blocks"]["questions"][str(i)] = q_bubbles

    # Candidate and Invigilator Signatures Box at Bottom
    sig_y = height - 170
    cv2.rectangle(img, (150, sig_y), (650, sig_y + 70), (0, 0, 0), 1)
    cv2.putText(img, "CANDIDATE SIGNATURE", (260, sig_y + 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50, 50, 50), 1)

    cv2.rectangle(img, (950, sig_y), (1450, sig_y + 70), (0, 0, 0), 1)
    cv2.putText(img, "INVIGILATOR SIGNATURE & STAMP", (1030, sig_y + 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50, 50, 50), 1)

    # Save PNG blank image
    png_path = os.path.join(output_dir, "omr_sheet_blank.png")
    cv2.imwrite(png_path, img)

    # Save PDF blank document
    pdf_path = os.path.join(output_dir, "omr_sheet_blank.pdf")
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    pil_img.save(pdf_path, "PDF", resolution=150.0)

    # Save template JSON
    template_path = os.path.join(output_dir, "omr_template.json")
    with open(template_path, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2)

    # Also save template JSON to backend/app/omr/templates/standard_omr_template.json
    backend_template_dir = "./backend/app/omr/templates"
    os.makedirs(backend_template_dir, exist_ok=True)
    backend_template_path = os.path.join(backend_template_dir, "standard_omr_template.json")
    with open(backend_template_path, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2)

    return template


if __name__ == "__main__":
    t = generate_standard_omr_sheet()
    print("Standard blank OMR sheet and template JSON successfully generated!")
