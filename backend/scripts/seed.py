import sys
import os

# Ensure workspace root in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.core.security import get_password_hash
from backend.app.db.session import SessionLocal, Base, engine
from backend.app.models.models import (
    User,
    UserRole,
    Exam,
    AnswerKey,
    MultiMarkedRule,
)


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("Seeding database...")

        # 1. Admin User
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                email="admin@omr.local",
                hashed_password=get_password_hash("Admin@12345"),
                role=UserRole.ADMIN.value,
                is_active=True,
            )
            db.add(admin_user)
            print("Created admin user: admin / Admin@12345")
        else:
            print("Admin user already exists.")

        # 2. Operator User
        operator_user = db.query(User).filter(User.username == "operator").first()
        if not operator_user:
            operator_user = User(
                username="operator",
                email="operator@omr.local",
                hashed_password=get_password_hash("Operator@12345"),
                role=UserRole.OPERATOR.value,
                is_active=True,
            )
            db.add(operator_user)
            print("Created operator user: operator / Operator@12345")
        else:
            print("Operator user already exists.")

        # 3. Sample Exam
        sample_exam = db.query(Exam).filter(Exam.code == "GSM-2026").first()
        if not sample_exam:
            sample_exam = Exam(
                name="General Science & Mathematics 2026",
                code="GSM-2026",
                total_questions=50,
                marks_per_correct=4.0,
                negative_marks=1.0,
                multi_marked_rule=MultiMarkedRule.COUNT_AS_WRONG.value,
                is_active=True,
            )
            db.add(sample_exam)
            db.commit()
            db.refresh(sample_exam)
            print(f"Created sample exam: {sample_exam.name} ({sample_exam.code})")

            # 4. Answer Keys for Set A and Set B
            options = ["A", "B", "C", "D"]
            keys_to_add = []
            for q in range(1, 51):
                # Deterministic pattern for sample sets
                correct_a = options[(q - 1) % 4]
                correct_b = options[(q + 1) % 4]
                keys_to_add.append(
                    AnswerKey(
                        exam_id=sample_exam.id,
                        set_code="A",
                        question_no=q,
                        correct_option=correct_a,
                    )
                )
                keys_to_add.append(
                    AnswerKey(
                        exam_id=sample_exam.id,
                        set_code="B",
                        question_no=q,
                        correct_option=correct_b,
                    )
                )
            db.add_all(keys_to_add)
            print("Added 50 answer keys each for Set A and Set B.")
        else:
            print("Sample exam GSM-2026 already exists.")

        db.commit()
        print("Database seeding completed successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
