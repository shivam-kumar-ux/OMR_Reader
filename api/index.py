"""
Vercel Serverless Function Entry Point for OMR Web Application.
Mounts FastAPI app for serverless execution.
"""

import sys
import os

# Add root project directory to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.app.main import app
