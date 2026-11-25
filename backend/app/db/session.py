import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from backend.app.core.config import settings

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

    if "pg8000" in driver and "channel_binding" in db_url:
        db_url = db_url.replace("&channel_binding=require", "").replace("?channel_binding=require&", "?").replace("?channel_binding=require", "")

    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", driver, 1)
    elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
        db_url = db_url.replace("postgresql://", driver, 1)

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

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
