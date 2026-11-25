"""
Entry point for backend service when root is set to 'backend'.
"""
import sys
import os

backend_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(backend_dir, ".."))

for d in [root_dir, backend_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

from backend.app.main import app

__all__ = ["app"]
