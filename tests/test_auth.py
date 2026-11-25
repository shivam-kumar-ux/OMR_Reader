import datetime
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from backend.app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
)
from backend.app.db.session import SessionLocal, engine, Base
from backend.app.models.models import User, UserRole
from backend.app.schemas.auth import UserLogin
from backend.app.schemas.user import UserCreate, UserUpdate
from backend.app.api.deps import get_current_user, require_admin, require_operator
from backend.app.api.v1.auth import login, get_current_user_profile
from backend.app.api.v1.users import list_users, create_user, update_user


@pytest.fixture(autouse=True)
def ensure_db():
    Base.metadata.create_all(bind=engine)
    yield


def test_password_hashing():
    pw = "SuperSecretPassword123!"
    hashed = get_password_hash(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_creation_and_decoding():
    token = create_access_token(
        subject=42,
        role="Admin",
        expires_delta=datetime.timedelta(minutes=15),
        extra_claims={"username": "superadmin"},
    )
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "Admin"
    assert payload["username"] == "superadmin"


def test_login_flow_and_dependencies():
    db = SessionLocal()
    try:
        # Create test users
        db.query(User).filter(User.username.in_(["auth_admin_test", "auth_oper_test"])).delete()
        db.commit()

        admin = User(
            username="auth_admin_test",
            email="admin_test@test.com",
            hashed_password=get_password_hash("AdminPass123"),
            role=UserRole.ADMIN.value,
            is_active=True,
        )
        operator = User(
            username="auth_oper_test",
            email="oper_test@test.com",
            hashed_password=get_password_hash("OperPass123"),
            role=UserRole.OPERATOR.value,
            is_active=True,
        )
        db.add_all([admin, operator])
        db.commit()
        db.refresh(admin)
        db.refresh(operator)

        # 1. Invalid login attempt -> 401
        with pytest.raises(HTTPException) as exc_info:
            login(UserLogin(username="auth_admin_test", password="WrongPassword"), db=db)
        assert exc_info.value.status_code == 401

        # 2. Non-existent user -> 401
        with pytest.raises(HTTPException) as exc_info:
            login(UserLogin(username="unknown_user", password="AnyPassword"), db=db)
        assert exc_info.value.status_code == 401

        # 3. Successful admin login
        admin_token_data = login(UserLogin(username="auth_admin_test", password="AdminPass123"), db=db)
        assert admin_token_data.access_token is not None
        assert admin_token_data.role == "Admin"
        assert admin_token_data.username == "auth_admin_test"

        # 4. Successful operator login
        oper_token_data = login(UserLogin(username="auth_oper_test", password="OperPass123"), db=db)
        assert oper_token_data.role == "Operator"

        # 5. Dependency: get_current_user with valid token
        creds_admin = HTTPAuthorizationCredentials(scheme="Bearer", credentials=admin_token_data.access_token)
        curr_admin = get_current_user(auth=creds_admin, db=db)
        assert curr_admin.username == "auth_admin_test"

        creds_oper = HTTPAuthorizationCredentials(scheme="Bearer", credentials=oper_token_data.access_token)
        curr_oper = get_current_user(auth=creds_oper, db=db)
        assert curr_oper.username == "auth_oper_test"

        # 6. Dependency: get_current_user with invalid token -> 401
        bad_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.jwt.token")
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(auth=bad_creds, db=db)
        assert exc_info.value.status_code == 401

        # 7. Role check: require_admin
        admin_checked = require_admin(curr_admin)
        assert admin_checked.id == curr_admin.id

        with pytest.raises(HTTPException) as exc_info:
            require_admin(curr_oper)
        assert exc_info.value.status_code == 403

        # 8. Role check: require_operator accepts both Admin and Operator
        assert require_operator(curr_admin).id == curr_admin.id
        assert require_operator(curr_oper).id == curr_oper.id

    finally:
        db.close()


def test_admin_crud_users():
    db = SessionLocal()
    try:
        # Clean up test user if exists
        db.query(User).filter(User.username == "test_created_staff").delete()
        db.commit()

        admin = db.query(User).filter(User.role == UserRole.ADMIN.value).first()
        if not admin:
            admin = User(
                username="temp_admin",
                email="temp_admin@omr.local",
                hashed_password=get_password_hash("AdminPass123"),
                role=UserRole.ADMIN.value,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)

        # Create new user via create_user endpoint
        new_user_in = UserCreate(
            username="test_created_staff",
            email="staff@omr.local",
            password="SecureStaffPass123",
            role=UserRole.OPERATOR,
        )
        created = create_user(user_in=new_user_in, current_admin=admin, db=db)
        assert created.id is not None
        assert created.username == "test_created_staff"
        assert created.role == "Operator"

        # List users
        all_users = list_users(skip=0, limit=100, current_admin=admin, db=db)
        assert any(u.id == created.id for u in all_users)

        # Update user
        updated = update_user(
            user_id=created.id,
            user_in=UserUpdate(is_active=False),
            current_admin=admin,
            db=db,
        )
        assert updated.is_active is False
    finally:
        db.close()
