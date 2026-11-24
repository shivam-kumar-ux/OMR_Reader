"""
Unit tests for Report Generation (PDF/Excel) and Admin Endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.models.models import User, UserRole, Exam, Student, Result, StudentAnswer, AuditLog
from backend.app.services.report_generator import (
    generate_exam_pdf_report,
    generate_student_card_pdf,
    generate_exam_excel_report
)

client = TestClient(app)


@pytest.fixture
def auth_admin():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin_test").first()
        if not user:
            user = User(
                username="admin_test",
                email="admin_test@example.com",
                hashed_password="hashed_pw",
                role=UserRole.ADMIN.value,
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        user_id = user.id
    finally:
        db.close()

    from backend.app.core.security import create_access_token
    token = create_access_token(subject=str(user_id), role="admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seeded_report_data():
    db = SessionLocal()
    try:
        # Create or fetch exam
        exam = db.query(Exam).filter(Exam.code == "RPT-101").first()
        if not exam:
            exam = Exam(
                name="Reporting Test Exam",
                code="RPT-101",
                total_questions=50,
                marks_per_correct=2.0,
                negative_marks=0.5
            )
            db.add(exam)
            db.commit()
            db.refresh(exam)

        # Create student
        student = db.query(Student).filter(Student.roll_no == "990011").first()
        if not student:
            student = Student(
                roll_no="990011",
                name_final="ALICE SMITH",
                father_name_final="BOB SMITH",
                mobile_final="9876543210",
                class_name_final="12A",
                dob_final="2005-01-01"
            )
            db.add(student)
            db.commit()
            db.refresh(student)

        # Create result
        result = db.query(Result).filter(Result.student_id == student.id, Result.exam_id == exam.id).first()
        if not result:
            result = Result(
                student_id=student.id,
                exam_id=exam.id,
                set_code="A",
                total_score=85.0,
                correct_count=45,
                wrong_count=5,
                not_attempted_count=0,
                status="AUTO_ACCEPTED",
                confidence_score=0.98
            )
            db.add(result)
            db.commit()
            db.refresh(result)

            # Add answers
            for q in range(1, 51):
                ans = StudentAnswer(
                    result_id=result.id,
                    question_no=q,
                    marked_option="A",
                    is_correct=(q <= 45),
                    confidence=0.99
                )
                db.add(ans)
            db.commit()

        # Add an audit log entry
        log = AuditLog(
            user_id=1,
            action="TEST_ACTION",
            entity_type="exam",
            entity_id=str(exam.id),
            new_values='{"msg": "Reporting test"}'
        )
        db.add(log)
        db.commit()

        return {
            "exam_id": exam.id,
            "student_id": student.id,
            "result_id": result.id
        }
    finally:
        db.close()


def test_pdf_report_generators_direct(seeded_report_data):
    db = SessionLocal()
    try:
        exam = db.query(Exam).filter(Exam.id == seeded_report_data["exam_id"]).first()
        student = db.query(Student).filter(Student.id == seeded_report_data["student_id"]).first()
        result = db.query(Result).filter(Result.id == seeded_report_data["result_id"]).first()
        answers = db.query(StudentAnswer).filter(StudentAnswer.result_id == result.id).all()

        # 1. Exam summary PDF
        exam_pdf = generate_exam_pdf_report(exam, [result])
        assert isinstance(exam_pdf, bytes)
        assert exam_pdf.startswith(b"%PDF-")

        # 2. Student scorecard PDF
        student_pdf = generate_student_card_pdf(exam, student, result, answers)
        assert isinstance(student_pdf, bytes)
        assert student_pdf.startswith(b"%PDF-")

        # 3. Excel report
        excel_bytes = generate_exam_excel_report(exam, [result])
        assert isinstance(excel_bytes, bytes)
        assert excel_bytes.startswith(b"PK")  # ZIP signature
    finally:
        db.close()


def test_reports_api_endpoints(auth_admin, seeded_report_data):
    exam_id = seeded_report_data["exam_id"]
    result_id = seeded_report_data["result_id"]

    # Test PDF Exam Download
    res = client.get(f"/api/v1/reports/exam/{exam_id}/pdf", headers=auth_admin)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF-")

    # Test Excel Exam Download
    res = client.get(f"/api/v1/reports/exam/{exam_id}/excel", headers=auth_admin)
    assert res.status_code == 200
    assert "spreadsheetml" in res.headers["content-type"]
    assert res.content.startswith(b"PK")

    # Test Student Scorecard PDF Download
    res = client.get(f"/api/v1/reports/result/{result_id}/pdf", headers=auth_admin)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF-")


def test_admin_audit_logs_and_settings(auth_admin):
    # Get Audit Logs
    res = client.get("/api/v1/admin/audit-logs", headers=auth_admin)
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "items" in data

    # Get Settings
    res = client.get("/api/v1/admin/settings", headers=auth_admin)
    assert res.status_code == 200
    settings_data = res.json()
    assert "BUBBLE_FILL_THRESHOLD" in settings_data

    # Update Settings
    res = client.put(
        "/api/v1/admin/settings",
        json={"BUBBLE_FILL_THRESHOLD": 0.46},
        headers=auth_admin
    )
    assert res.status_code == 200
    assert res.json()["settings"]["BUBBLE_FILL_THRESHOLD"] == 0.46
