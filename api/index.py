"""
Serverless entry point for FastAPI on Vercel.
Resolves backend packages cleanly and exposes the FastAPI app instance.
"""
import sys
import os

api_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(api_dir, ".."))
backend_dir = os.path.join(root_dir, "backend")

for d in [root_dir, backend_dir, api_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

from backend.app.main import app

__all__ = ["app"]
