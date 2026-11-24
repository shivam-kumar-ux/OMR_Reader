from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.api.v1 import api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager:
    Auto-initialize database tables and seed default admin on startup.
    Ensures zero-setup cloud deployment on serverless platforms (Vercel, etc.).
    """
    try:
        from backend.app.db.session import engine, Base, SessionLocal
        Base.metadata.create_all(bind=engine)

        from backend.app.models.models import User, UserRole
        from backend.app.core.security import get_password_hash
        with SessionLocal() as db:
            admin_user = db.query(User).filter(User.username == "admin").first()
            if not admin_user:
                admin = User(
                    username="admin",
                    email="admin@omr.local",
                    hashed_password=get_password_hash("Admin@12345"),
                    role=UserRole.ADMIN.value,
                    is_active=True,
                )
                db.add(admin)
                db.commit()
    except Exception as e:
        print(f"Startup DB init notice: {e}")
    yield


app = FastAPI(
    title="OMR Recognition System API",
    description="High-precision Optical Mark Recognition and evaluation platform with SQL Server backend",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.ENVIRONMENT != "development" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_v1_router)


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "storage_provider": settings.STORAGE_PROVIDER,
    }
