"""
UI-enabled entry point.

Run:
    uvicorn app.main_with_ui:app --reload --port 8000

This imports the existing application without modifying app/main.py,
then attaches the frontend dashboard.
"""

from app.frontend import attach_frontend
from app.main import app


attach_frontend(app)
