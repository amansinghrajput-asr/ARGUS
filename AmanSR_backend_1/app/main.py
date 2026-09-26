"""FastAPI application entry point for ARGUS Backend 1."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from .core.config import settings
from .core.database import connect_to_database, close_database_connection
from .api.router import api_router


@asynccontextmanager
async def lifespan(app: Any) -> AsyncGenerator[None, None]:  # type: ignore[name-defined]
    """Manage application startup and shutdown lifecycle."""
    # Startup: connect to MongoDB
    await connect_to_database()
    yield
    # Shutdown: clean up database connection
    await close_database_connection()


try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(
        title=settings.app_name,
        description="ARGUS Customer Support Intelligence System — Backend 1 API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Enable CORS for ARGUS frontends
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"])
    async def health_check() -> dict:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": settings.app_name,
            "environment": settings.app_env,
        }

    # Mount API routes
    app.include_router(api_router)

except ImportError:
    # Minimal stub when fastapi is not yet installed in local environment
    class MockApp:
        def __init__(self) -> None:
            self.title = settings.app_name
            self.version = "0.1.0"

        def get_health(self) -> dict:
            return {"status": "healthy", "service": self.title}

    app = MockApp()  # type: ignore[assignment]


if __name__ == "__main__":
    try:
        import uvicorn
        uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
    except ImportError:
        print("uvicorn is not installed. Run 'pip install -r requirements.txt'")
