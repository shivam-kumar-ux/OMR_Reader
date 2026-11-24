from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from backend.app.core.config import settings

# Engine configuration with NullPool for serverless / Azure SQL
engine_kwargs = {
    "echo": False,
    "future": True,
}

# Normalize postgres:// URLs (common in Neon, Supabase, Heroku) to postgresql://
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

if db_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Use NullPool for serverless environments (Vercel, Lambda, Neon, Supabase)
    if settings.IS_SERVERLESS or any(k in db_url.lower() for k in ["azure", "neon", "supabase", "pooler"]):
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_recycle"] = 1800

engine = create_engine(db_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
