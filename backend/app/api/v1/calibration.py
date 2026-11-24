import base64
import json
import os
import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response, status
from sqlalchemy.orm import Session

from backend.app.api.deps import require_operator, get_current_user
from backend.app.db.session import get_db
from backend.app.models.models import User
from backend.app.omr.calibration import OMRCalibrator

router = APIRouter(prefix="/omr", tags=["OMR Calibration & Templates"])


@router.get("/template")
def get_template(current_user: User = Depends(get_current_user)):
    """Returns the standard OMR template JSON structure."""
    template_path = "./backend/app/omr/templates/standard_omr_template.json"
    if not os.path.exists(template_path):
        from backend.app.omr.generator import generate_standard_omr_sheet
        generate_standard_omr_sheet()

    calibrator = OMRCalibrator(template_path)
    return calibrator.template


@router.get("/calibrate/default")
def calibrate_default_sheet(
    format: str = "json",  # "json" (with base64 image) or "image" (binary jpeg)
    current_user: User = Depends(get_current_user),
):
    """
    Overlays the standard template on the default blank sheet to verify alignment visually.
    """
    blank_path = "./samples/blank/omr_sheet_blank.png"
    if not os.path.exists(blank_path):
        from backend.app.omr.generator import generate_standard_omr_sheet
        generate_standard_omr_sheet()

    img = cv2.imread(blank_path)
    if img is None:
        raise HTTPException(status_code=500, detail="Failed to load blank sheet image")

    calibrator = OMRCalibrator()
    overlay, stats = calibrator.overlay_calibration(img)

    success, buffer = cv2.imencode(".jpg", overlay, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not success:
        raise HTTPException(status_code=500, detail="Failed to encode calibration overlay image")

    if format == "image":
        return Response(content=buffer.tobytes(), media_type="image/jpeg")

    img_b64 = base64.b64encode(buffer).decode("utf-8")
    return {
        "status": "success",
        "stats": stats,
        "image_data": f"data:image/jpeg;base64,{img_b64}",
    }


@router.post("/calibrate/upload")
def calibrate_uploaded_sheet(
    file: UploadFile = File(...),
    custom_template: str = None,
    current_user: User = Depends(require_operator),
):
    """
    Upload a blank or scanned sheet (and optional custom template JSON) to generate a calibration overlay.
    """
    contents = file.file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image")

    calibrator = OMRCalibrator()
    template_data = calibrator.template
    if custom_template:
        try:
            template_data = json.loads(custom_template)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid custom template JSON")

    overlay, stats = calibrator.overlay_calibration(img, template=template_data)

    success, buffer = cv2.imencode(".jpg", overlay, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not success:
        raise HTTPException(status_code=500, detail="Failed to encode overlay image")

    img_b64 = base64.b64encode(buffer).decode("utf-8")
    return {
        "status": "success",
        "stats": stats,
        "image_data": f"data:image/jpeg;base64,{img_b64}",
    }
