import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from backend.app.models.models import MultiMarkedRule


class AnswerKeyItem(BaseModel):
    question_no: int = Field(..., ge=1, le=500)
    correct_option: str = Field(..., pattern=r"^[A-E]$")


class AnswerKeyCreate(BaseModel):
    set_code: str = Field(..., pattern=r"^[A-Z0-9]{1,10}$")
    keys: List[AnswerKeyItem]


class AnswerKeyResponse(BaseModel):
    id: int
    exam_id: int
    set_code: str
    question_no: int
    correct_option: str

    model_config = ConfigDict(from_attributes=True)


class ExamBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    code: str = Field(..., min_length=2, max_length=50)
    total_questions: int = Field(default=100, ge=1, le=500)
    marks_per_correct: float = Field(default=1.0, ge=0.0)
    negative_marks: float = Field(default=0.25, ge=0.0)
    multi_marked_rule: MultiMarkedRule = MultiMarkedRule.COUNT_AS_WRONG
    is_active: bool = True


class ExamCreate(ExamBase):
    pass


class ExamUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    total_questions: Optional[int] = Field(default=None, ge=1, le=500)
    marks_per_correct: Optional[float] = Field(default=None, ge=0.0)
    negative_marks: Optional[float] = Field(default=None, ge=0.0)
    multi_marked_rule: Optional[MultiMarkedRule] = None
    is_active: Optional[bool] = None


class ExamResponse(ExamBase):
    id: int
    created_at: datetime.datetime
    sets: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class ExamDetailResponse(ExamResponse):
    answer_keys: Dict[str, Dict[int, str]] = {}
