"""
Root entry point for FastAPI backend on Vercel Services.
Exposes the FastAPI app instance for serverless runtime.
"""
import sys
import os

root_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(root_dir, "backend")

for d in [root_dir, backend_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

from backend.app.main import app

__all__ = ["app"]
