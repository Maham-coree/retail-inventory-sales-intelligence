"""FastAPI application setup, middleware, health checks, and exception handling."""

import logging
import time
from pathlib import Path

from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .config import settings
from .database import engine
from .deps import get_current_user
from .logging_config import configure_logging
from .routers import auth, chatbot, labs, operations, resources
from .routers.resources import db_error

configure_logging()
logger = logging.getLogger(__name__)
app = FastAPI(
    title="Retail Inventory and Sales Intelligence API",
    version="1.0.0",
    description="Retail operations, sales, reporting, and database demonstrations.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static",
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - started) * 1000
        logger.exception(
            "request failed method=%s path=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            duration_ms,
        )
        raise
    duration_ms = (time.perf_counter() - started) * 1000
    logger.info(
        "request method=%s path=%s status=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    del request
    mapped = db_error(exc)
    return JSONResponse(
        status_code=mapped.status_code,
        content={"detail": mapped.detail},
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled request exception path=%s", request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected server error occurred"},
    )


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health", tags=["health"], summary="Check API process health")
def health() -> dict[str, str]:
    return {"message": "Retail Inventory API is running", "docs": "/docs"}


@app.get("/health/db", tags=["health"], summary="Check PostgreSQL connectivity")
def database_health() -> dict[str, str]:
    with engine.connect() as connection:
        version = connection.execute(text("SELECT version()")).scalar_one()
    return {"status": "ok", "database": "postgresql", "version": version}


@app.get("/database-design", include_in_schema=False)
def database_design(
    _: dict[str, object] = Depends(get_current_user),
) -> FileResponse:
    design_file = Path(__file__).resolve().parents[2] / "docs" / "database_design_documentation.md"
    return FileResponse(design_file, media_type="text/plain; charset=utf-8")


app.include_router(auth.router)
app.include_router(chatbot.router)
app.include_router(resources.router)
app.include_router(operations.router)
app.include_router(labs.router)
