"""
Root entry point for FastAPI backend on Vercel Services.
Exposes the FastAPI app instance for serverless runtime with diagnostic fallback.
"""
import sys
import os
import traceback

root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

backend_dir = os.path.join(root_dir, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from backend.app.main import app
except Exception as init_err:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    app = FastAPI(title="Diagnostic Fallback API")
    tb = traceback.format_exc()

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
    async def diagnostic_fallback(full_path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "FastAPI Startup Initialization Failed",
                "exception": str(init_err),
                "type": type(init_err).__name__,
                "traceback": tb.splitlines(),
            }
        )

__all__ = ["app"]
