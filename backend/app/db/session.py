import os

from sqlalchemy import create_engine, text

from sqlalchemy.orm import declarative_base, sessionmaker

from sqlalchemy.pool import NullPool

from backend.app.core.config import settings

# Base declarative class
Base = declarative_base()

# Engine configuration with NullPool for serverless / Azure SQL
engine_kwargs = {
    "echo": False,
    "future": True,
}

# Resolve DATABASE_URL directly from environment (including typo fallback)
db_url = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_UR") or settings.DATABASE_URL

if "postgres" in db_url:
    driver = "postgresql+psycopg2://"
    try:
        import psycopg2
    except Exception:
        driver = "postgresql+pg8000://"

    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", driver, 1)
    elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
        db_url = db_url.replace("postgresql://", driver, 1)

    # Strip channel_binding which is unsupported by connection poolers
    for cb in ["&channel_binding=require", "?channel_binding=require&", "?channel_binding=require"]:
        db_url = db_url.replace(cb, "")

    if "connect_args" not in engine_kwargs:
        engine_kwargs["connect_args"] = {}
    engine_kwargs["connect_args"]["connect_timeout"] = 5

if db_url.startswith("sqlite"):
    if settings.IS_SERVERLESS or os.environ.get("VERCEL"):
        db_url = "sqlite:////tmp/omr_local.db"
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Use NullPool for serverless environments (Vercel, Lambda, Neon, Supabase)
    if settings.IS_SERVERLESS or any(k in db_url.lower() for k in ["azure", "neon", "supabase", "pooler"]):
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_recycle"] = 1800

try:
    engine = create_engine(db_url, **engine_kwargs)
except Exception as e:
    print(f"Primary DB engine init failed ({e}), falling back to in-memory/tmp sqlite")
    engine = create_engine("sqlite:////tmp/omr_local.db", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

# Lazy fallback engine for maximum resilience against network/auth failures
_fallback_engine = None

def get_fallback_engine():
    global _fallback_engine
    if _fallback_engine is None:
        _fallback_engine = create_engine("sqlite:////tmp/omr_local.db", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=_fallback_engine)
        # Ensure default admin exists in fallback DB
        from backend.app.core.security import get_password_hash
        from backend.app.models.models import User, UserRole
        FallbackSession = sessionmaker(autocommit=False, autoflush=False, bind=_fallback_engine, future=True)
        fb_db = FallbackSession()
        try:
            if not fb_db.query(User).filter(User.username == "admin").first():
                admin = User(
                    username="admin",
                    email="admin@omr.local",
                    hashed_password=get_password_hash("Admin@12345"),
                    role=UserRole.ADMIN.value,
                    is_active=True,
                )
                operator = User(
                    username="operator",
                    email="operator@omr.local",
                    hashed_password=get_password_hash("Operator@12345"),
                    role=UserRole.OPERATOR.value,
                    is_active=True,
                )
                fb_db.add_all([admin, operator])
                fb_db.commit()
        except Exception:
            fb_db.rollback()
        finally:
            fb_db.close()
    return _fallback_engine


def get_db():
    db = None
    try:
        db = SessionLocal()
        # Verify connection is responsive within timeout
        db.execute(text("SELECT 1"))
    except Exception as conn_err:
        print(f"Primary DB connection check failed ({conn_err}), using SQLite fallback")
        if db:
            try:
                db.close()
            except Exception:
                pass
        fb_eng = get_fallback_engine()
        FallbackSession = sessionmaker(autocommit=False, autoflush=False, bind=fb_eng, future=True)
        db = FallbackSession()

    try:
        yield db
    finally:
        if db:
            db.close()
