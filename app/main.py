from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
import os
import pathlib

from app.config import get_settings
from app.database import engine, Base
from app.routes import widgets, public, dashboard

# Initialize database tables
Base.metadata.create_all(bind=engine)

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="A resilient, multi-tenant embeddable widget and lead-capture platform."
)

# ---------------------------------------------------------
# CORS Configuration (Allows Cross-Origin requests & Preflight)
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Public embeddable widgets can run on any customer domain
    allow_credentials=False,
    allow_methods=["*"],  # Handles GET, POST, OPTIONS preflight
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Static Asset Delivery with Cache Headers
# ---------------------------------------------------------
static_dir = pathlib.Path(__file__).parent / "static"
os.makedirs(static_dir, exist_ok=True)

# Mount static directory for general static files
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/widget.js", tags=["Widget Delivery"])
@app.get("/widget.v1.js", tags=["Widget Delivery"])
def serve_widget_script():
    """Serves the widget script directly with HTTP caching headers (Cache-Control)."""
    script_path = static_dir / "widget.js"
    return FileResponse(
        path=str(script_path),
        media_type="application/javascript",
        headers={
            "Cache-Control": "public, max-age=3600, immutable",
            "Access-Control-Allow-Origin": "*"
        }
    )


# ---------------------------------------------------------
# Clean Validation Error Handler (Boundary Validation)
# ---------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Formats validation errors into clean 422 JSON errors instead of unhandled 500s."""
    errors = []
    for err in exc.errors():
        field_loc = " -> ".join(str(loc) for loc in err.get("loc", []))
        errors.append(f"{field_loc}: {err.get('msg')}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "error_type": "ValidationError",
            "detail": "; ".join(errors),
            "raw_errors": exc.errors()
        }
    )


# ---------------------------------------------------------
# Include API Routers
# ---------------------------------------------------------
app.include_router(public.router)
app.include_router(widgets.router)
app.include_router(dashboard.router)


@app.get("/", tags=["Health"])
def health_check():
    """Health check and platform status info."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "docs_url": "/docs",
        "version": "1.0.0"
    }
