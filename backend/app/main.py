"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.routes import analyze, health, ndvi, rasters, study_area
from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging import setup_logging

WEB_DIR = Path(__file__).resolve().parent / "web"
STATIC_DIR = WEB_DIR / "static"

API_DESCRIPTION = """
## GeoAI Urban Satellite Change Detection

Research prototype API for multi-temporal urban change analysis over **Muscat / Oman**.

### Capabilities
- Study-area catalog (national + city AOIs)
- Full analysis pipeline (`baseline` or `cva`)
- NDVI / NDBI metrics and extended statistics
- GeoJSON change regions + PNG map overlays

### Quick links
- Portal home: [`/`](/)
- Swagger UI: [`/docs`](/docs)
- ReDoc: [`/redoc`](/redoc)

> **Disclaimer:** Research prototype — validate outputs before operational decisions.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    settings.ensure_directories()
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description=API_DESCRIPTION,
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        swagger_ui_parameters={
            "docExpansion": "list",
            "defaultModelsExpandDepth": 0,
            "displayRequestDuration": True,
            "filter": True,
            "tryItOutEnabled": True,
            "syntaxHighlight.theme": "obsidian",
        },
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False, response_class=HTMLResponse)
    def portal() -> FileResponse:
        return FileResponse(WEB_DIR / "portal.html")

    @app.get("/docs", include_in_schema=False)
    def custom_swagger() -> HTMLResponse:
        # Keep official Swagger CSS, then layer GeoAI theme on top
        html = get_swagger_ui_html(
            openapi_url=app.openapi_url or "/openapi.json",
            title=f"{settings.app_name} · Docs",
            swagger_favicon_url="/static/favicon.svg",
            swagger_ui_parameters={
                "docExpansion": "list",
                "defaultModelsExpandDepth": 0,
                "displayRequestDuration": True,
                "filter": True,
                "tryItOutEnabled": True,
                "syntaxHighlight.theme": "obsidian",
            },
        )
        banner = """
        <div class="geoai-docs-banner">
          <div class="brand">GeoAI API Console</div>
          <a href="/">Portal</a>
          <a href="/redoc">ReDoc</a>
          <a href="/openapi.json">OpenAPI JSON</a>
          <a href="http://127.0.0.1:5173" target="_blank" rel="noreferrer">Dashboard</a>
        </div>
        """
        content = html.body.decode("utf-8")
        content = content.replace(
            "</head>",
            '<link rel="stylesheet" type="text/css" href="/static/swagger-theme.css"></head>',
            1,
        )
        content = content.replace("<body>", f"<body>{banner}", 1)
        return HTMLResponse(content=content)

    @app.get("/redoc", include_in_schema=False)
    def custom_redoc() -> HTMLResponse:
        return get_redoc_html(
            openapi_url=app.openapi_url or "/openapi.json",
            title=f"{settings.app_name} · ReDoc",
            redoc_favicon_url="/static/favicon.svg",
        )

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> FileResponse:
        path = STATIC_DIR / "favicon.svg"
        if path.exists():
            return FileResponse(path, media_type="image/svg+xml")
        return Response(status_code=204)

    app.include_router(health.router, prefix="/api")
    app.include_router(study_area.router, prefix="/api")
    app.include_router(analyze.router, prefix="/api")
    app.include_router(ndvi.router, prefix="/api")
    app.include_router(rasters.router, prefix="/api")
    return app


app = create_app()
