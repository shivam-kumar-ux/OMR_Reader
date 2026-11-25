import os

from sqlalchemy import create_engine, text

from sqlalchemy.orm import declarative_base, sessionmaker

from sqlalchemy.pool import NullPool

from backend.app.core.config import settings

# Base declarative class
Base = declarative_base()

# Engine configuration
engine_kwargs = {
    "echo": False,
    "future": True,
}

# Get database URL - prefer environment variable
db_url = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_UR") or settings.DATABASE_URL

# If no URL or invalid, default to SQLite
if not db_url or db_url.strip() == "":
    db_url = "sqlite:////tmp/omr_local.db"
    print("No DATABASE_URL provided, using SQLite fallback")

# Configure for PostgreSQL if that's what's provided
if "postgres" in db_url.lower():
    driver = "postgresql+psycopg2://"
    try:
        import psycopg2
    except Exception:
        driver = "postgresql+pg8000://"

    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", driver, 1)
    elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
        db_url = db_url.replace("postgresql://", driver, 1)

    # Strip channel_binding parameter - incompatible with serverless
    for cb in ["&channel_binding=require", "?channel_binding=require&", "?channel_binding=require"]:
        db_url = db_url.replace(cb, "")

    if "connect_args" not in engine_kwargs:
        engine_kwargs["connect_args"] = {}
    engine_kwargs["connect_args"]["connect_timeout"] = 5
    
    # Use NullPool for serverless
    engine_kwargs["poolclass"] = NullPool

# Configure for SQLite
if db_url.startswith("sqlite"):
    # Always use /tmp for serverless environments
    if os.environ.get("VERCEL") or settings.IS_SERVERLESS:
        db_url = "sqlite:////tmp/omr_local.db"
    
    engine_kwargs["connect_args"] = {"check_same_thread": False}

# Try to create engine
try:
    engine = create_engine(db_url, **engine_kwargs)
    print(f"✅ Database engine initialized: {db_url[:50]}...")
except Exception as e:
    print(f"⚠️ Failed to initialize database engine: {e}")
    print("Falling back to SQLite")
    db_url = "sqlite:////tmp/omr_local.db"
    engine_kwargs = {"echo": False, "future": True, "connect_args": {"check_same_thread": False}}
    engine = create_engine(db_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

# Fallback engine for maximum resilience
_fallback_engine = None

def get_fallback_engine():
    global _fallback_engine
    if _fallback_engine is None:
        print("🔄 Initializing SQLite fallback engine...")
        _fallback_engine = create_engine("sqlite:////tmp/omr_local.db", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=_fallback_engine)
        
        # Seed default users
        from backend.app.core.security import get_password_hash
        from backend.app.models.models import User, UserRole
        
        FallbackSession = sessionmaker(autocommit=False, autoflush=False, bind=_fallback_engine, future=True)
        fb_db = FallbackSession()
        
        try:
            # Check if admin already exists
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
                print("✅ Seeded default admin and operator accounts")
        except Exception as e:
            print(f"⚠️ Could not seed fallback database: {e}")
            fb_db.rollback()
        finally:
            fb_db.close()
    
    return _fallback_engine


def get_db():
    """Get database session with automatic fallback to SQLite"""
    db = None
    try:
        db = SessionLocal()
        # Test connection
        db.execute(text("SELECT 1"))
        yield db
    except Exception as conn_err:
        print(f"⚠️ Primary database connection failed: {conn_err}")
        if db:
            try:
                db.close()
            except Exception:
                pass
        
        # Use fallback SQLite
        fb_eng = get_fallback_engine()
        FallbackSession = sessionmaker(autocommit=False, autoflush=False, bind=fb_eng, future=True)
        db = FallbackSession()
        try:
            yield db
        finally:
            if db:
                db.close()
    else:
        if db:
            db.close()
