from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict


class ScanFileStatus(BaseModel):
    filename: str
    page_number: int = 1
    status: str  # "done" (AUTO_ACCEPTED), "needs_review", "failed"
    result_id: Optional[int] = None
    student_id: Optional[int] = None
    roll_no: Optional[str] = None
    name: Optional[str] = None
    set_code: Optional[str] = None
    total_score: Optional[float] = None
    confidence_score: float = 0.0
    review_reasons: List[str] = []
    error_message: Optional[str] = None
    sheet_image_url: Optional[str] = None
    processed_image_url: Optional[str] = None


class BatchScanResponse(BaseModel):
    batch_id: str
    total_files_received: int
    total_sheets_processed: int
    auto_accepted_count: int
    needs_review_count: int
    failed_count: int
    results: List[ScanFileStatus]


class ReviewFieldConfirm(BaseModel):
    name_final: Optional[str] = None
    father_name_final: Optional[str] = None
    roll_no: Optional[str] = None
    mobile_final: Optional[str] = None
    dob_final: Optional[str] = None
    class_name_final: Optional[str] = None
    set_code: Optional[str] = None


class QuestionCorrection(BaseModel):
    question_no: int
    marked_option: Optional[str] = None  # "A", "B", "C", "D", or None


class ConfirmReviewRequest(BaseModel):
    result_id: int
    student_fields: ReviewFieldConfirm
    question_corrections: List[QuestionCorrection] = []
    comments: Optional[str] = None


class RecheckRequest(BaseModel):
    stricter_threshold: bool = True
    fill_threshold: Optional[float] = None
