import traceback
from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.db.session import Base, engine, get_fallback_engine
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

app = FastAPI(
    title="OMR Recognition System API",
    description="High-precision Optical Mark Recognition and evaluation platform",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        # Create tables in primary database
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables initialized")
        # Pre-initialize fallback
        get_fallback_engine()
        print("✅ Fallback database ready")
    except Exception as e:
        print(f"⚠️ Startup initialization error: {e}")

# Global exception handler to surface any server error clearly
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal Server Error: {str(exc)}",
            "type": type(exc).__name__,
        },
    )

# CORS setup - allow all origins for now (can be restricted later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.get("/test")
@app.get("/api/test")
def test_diagnostic():
    import os
    return {
        "status": "ok",
        "message": "FastAPI is responding normally!",
        "has_database_url": bool(os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_UR")),
        "db_provider": "postgres" if "postgres" in (os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_UR") or "") else "sqlite",
        "is_serverless": settings.IS_SERVERLESS,
    }
