from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"

router = APIRouter(include_in_schema=False)


@router.get("/", response_class=FileResponse)
def frontend_home() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@router.get("/ui", response_class=FileResponse)
def frontend_ui() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


def attach_frontend(app: FastAPI) -> None:
    """
    Attach the dashboard to an existing FastAPI application.

    The main project API remains unchanged:
    - POST /documents
    - POST /audits
    - GET  /audits/{audit_id}
    - GET  /health
    """

    app.mount(
        "/static",
        StaticFiles(directory=STATIC_DIR),
        name="static",
    )
    app.include_router(router)
