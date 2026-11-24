import datetime
from enum import Enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from backend.app.db.session import Base


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


class UserRole(str, Enum):
    ADMIN = "Admin"
    OPERATOR = "Operator"


class SheetStatus(str, Enum):
    AUTO_ACCEPTED = "AUTO_ACCEPTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class MultiMarkedRule(str, Enum):
    COUNT_AS_WRONG = "COUNT_AS_WRONG"
    COUNT_AS_NOT_ATTEMPTED = "COUNT_AS_NOT_ATTEMPTED"


class BubbleState(str, Enum):
    SINGLE = "SINGLE"
    EMPTY = "EMPTY"
    MULTI = "MULTI"
    UNCERTAIN = "UNCERTAIN"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default=UserRole.OPERATOR.value, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    audit_logs = relationship("AuditLog", back_populates="user")
    verified_students = relationship("Student", back_populates="verified_by_user")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    roll_no = Column(String(50), nullable=False, index=True)

    # Name fields
    name_bubble = Column(String(150), nullable=True)
    name_ocr = Column(String(150), nullable=True)
    name_final = Column(String(150), nullable=False)

    # Father's name
    father_name_bubble = Column(String(150), nullable=True)
    father_name_ocr = Column(String(150), nullable=True)
    father_name_final = Column(String(150), nullable=True)

    # Mobile
    mobile_bubble = Column(String(20), nullable=True)
    mobile_ocr = Column(String(20), nullable=True)
    mobile_final = Column(String(20), nullable=True)

    # Date of birth
    dob_bubble = Column(String(20), nullable=True)
    dob_ocr = Column(String(20), nullable=True)
    dob_final = Column(String(20), nullable=True)

    # Class
    class_name_bubble = Column(String(30), nullable=True)
    class_name_ocr = Column(String(30), nullable=True)
    class_name_final = Column(String(30), nullable=True)

    # Verification flag and verifier
    verified_flag = Column(Boolean, default=False, nullable=False)
    verified_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    verified_by_user = relationship("User", back_populates="verified_students")
    results = relationship("Result", back_populates="student", cascade="all, delete-orphan")


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    total_questions = Column(Integer, default=100, nullable=False)
    marks_per_correct = Column(Float, default=1.0, nullable=False)
    negative_marks = Column(Float, default=0.25, nullable=False)
    multi_marked_rule = Column(String(30), default=MultiMarkedRule.COUNT_AS_WRONG.value, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    answer_keys = relationship("AnswerKey", back_populates="exam", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="exam", cascade="all, delete-orphan")


class AnswerKey(Base):
    __tablename__ = "answer_keys"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    set_code = Column(String(10), nullable=False, default="A")
    question_no = Column(Integer, nullable=False)
    correct_option = Column(String(5), nullable=False)

    __table_args__ = (
        UniqueConstraint("exam_id", "set_code", "question_no", name="uq_exam_set_question"),
        Index("ix_answer_key_lookup", "exam_id", "set_code"),
    )

    exam = relationship("Exam", back_populates="answer_keys")


class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    set_code = Column(String(10), nullable=False, default="A")

    # Counts
    total_questions = Column(Integer, default=0, nullable=False)
    correct_count = Column(Integer, default=0, nullable=False)
    wrong_count = Column(Integer, default=0, nullable=False)
    not_attempted_count = Column(Integer, default=0, nullable=False)
    multi_marked_count = Column(Integer, default=0, nullable=False)

    # Scores
    total_score = Column(Float, default=0.0, nullable=False)
    percentage = Column(Float, default=0.0, nullable=False)

    # Status & Review
    status = Column(String(30), default=SheetStatus.NEEDS_REVIEW.value, nullable=False, index=True)
    review_reason = Column(Text, nullable=True)
    confidence_score = Column(Float, default=0.0, nullable=False)

    # Images
    sheet_image_path = Column(String(500), nullable=True)
    processed_image_path = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("student_id", "exam_id", name="uq_student_exam_result"),
        Index("ix_results_exam_status", "exam_id", "status"),
    )

    student = relationship("Student", back_populates="results")
    exam = relationship("Exam", back_populates="results")
    answers = relationship("StudentAnswer", back_populates="result", cascade="all, delete-orphan")


class StudentAnswer(Base):
    __tablename__ = "student_answers"

    id = Column(Integer, primary_key=True, index=True)
    result_id = Column(Integer, ForeignKey("results.id", ondelete="CASCADE"), nullable=False, index=True)
    question_no = Column(Integer, nullable=False)
    marked_option = Column(String(10), nullable=True)  # "A", "B", "AB", None
    is_correct = Column(Boolean, nullable=True)
    confidence = Column(Float, default=1.0, nullable=False)
    is_uncertain = Column(Boolean, default=False, nullable=False)
    status = Column(String(20), default=BubbleState.SINGLE.value, nullable=False)  # SINGLE, EMPTY, MULTI, UNCERTAIN

    __table_args__ = (
        UniqueConstraint("result_id", "question_no", name="uq_result_question"),
    )

    result = relationship("Result", back_populates="answers")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(50), nullable=False)
    old_values = Column(Text, nullable=True)
    new_values = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)

    user = relationship("User", back_populates="audit_logs")
