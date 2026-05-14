from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.domain.exceptions import NotFoundError, ValidationError
from app.lifespan import lifespan

settings = get_settings()
app = FastAPI(title=settings.project_name, lifespan=lifespan)


def _resolve_frontend_dist_dir() -> Path | None:
    """Resolve the frontend build directory if it exists."""
    if settings.frontend_dist_dir:
        frontend_dist_dir = Path(settings.frontend_dist_dir)
    else:
        frontend_dist_dir = Path(__file__).resolve().parents[2] / "frontend" / "dist"

    return frontend_dist_dir if frontend_dist_dir.exists() else None


def _is_backend_only_path(path: str) -> bool:
    """Return whether a path belongs to backend-owned routes."""
    normalized = path.strip("/")
    backend_prefixes = [settings.api_v1_prefix.strip("/"), "health", "assets"]
    return any(
        normalized == prefix or normalized.startswith(f"{prefix}/")
        for prefix in backend_prefixes
        if prefix
    )


frontend_dist_dir = _resolve_frontend_dist_dir()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)

if frontend_dist_dir is not None:
    assets_dir = frontend_dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    """Return a simple health status for uptime checks."""
    return {"status": "ok"}


@app.exception_handler(NotFoundError)
async def handle_not_found(_: Request, exc: NotFoundError) -> JSONResponse:
    """Map domain not-found errors to HTTP 404 responses."""
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ValidationError)
async def handle_validation_error(_: Request, exc: ValidationError) -> JSONResponse:
    """Map domain validation errors to HTTP 400 responses."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


if frontend_dist_dir is not None:
    @app.get("/", include_in_schema=False)
    async def frontend_index() -> FileResponse:
        """Serve the frontend index page for the root route."""
        return FileResponse(frontend_dist_dir / "index.html")


    @app.get("/{full_path:path}", include_in_schema=False)
    async def frontend_routes(full_path: str) -> FileResponse:
        """Serve frontend static files or fallback to index routing."""
        if _is_backend_only_path(full_path):
            raise HTTPException(status_code=404, detail="Not Found")

        candidate = frontend_dist_dir / full_path
        if candidate.is_file():
            return FileResponse(candidate)

        return FileResponse(frontend_dist_dir / "index.html")
