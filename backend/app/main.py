import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.api.v1 import api_v1_router
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.users import router as users_router
from backend.app.api.v1.exams import router as exams_router
from backend.app.api.v1.calibration import router as calibration_router
from backend.app.api.v1.scan import router as scan_router
from backend.app.api.v1.results import router as results_router
from backend.app.api.v1.students import router as students_router
from backend.app.api.v1.reports import router as reports_router
from backend.app.api.v1.admin import router as admin_router


def _init_db_sync():
    """Sync helper to initialize database tables and seed default admin."""
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Non-blocking lifespan context manager:
    Spawns background DB initialization thread so serverless cold start is immediate.
    """
    try:
        asyncio.create_task(asyncio.to_thread(_init_db_sync))
    except Exception as e:
        print(f"Lifespan task notice: {e}")
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

# Primary API routes (/api/v1/...)
app.include_router(api_v1_router)

# Secondary alias routes (/v1/...) for reverse proxy rewrite compatibility
v1_alias_router = APIRouter(prefix="/v1")
for r in [
    auth_router, users_router, exams_router, calibration_router,
    scan_router, results_router, students_router, reports_router, admin_router,
]:
    v1_alias_router.include_router(r)
app.include_router(v1_alias_router)


@app.get("/health")
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "storage_provider": settings.STORAGE_PROVIDER,
    }
