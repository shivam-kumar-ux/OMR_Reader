from fastapi import APIRouter
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.users import router as users_router
from backend.app.api.v1.exams import router as exams_router
from backend.app.api.v1.calibration import router as calibration_router
from backend.app.api.v1.scan import router as scan_router
from backend.app.api.v1.results import router as results_router
from backend.app.api.v1.students import router as students_router
from backend.app.api.v1.reports import router as reports_router
from backend.app.api.v1.admin import router as admin_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(exams_router)
api_v1_router.include_router(calibration_router)
api_v1_router.include_router(scan_router)
api_v1_router.include_router(results_router)
api_v1_router.include_router(students_router)
api_v1_router.include_router(reports_router)
api_v1_router.include_router(admin_router)
