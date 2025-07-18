"""
FastAPI Backend for CARLA Scenario Fuzzing Framework

Main application entry point that sets up the FastAPI server,
routes, middleware, and WebSocket connections.
"""

import sys
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from api.routes import experiments, scenarios, configurations, results, files, system
# from api.websockets import console_logs  # TODO: Fix import path
from core.config import get_settings


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting CARLA Fuzzing Framework Backend")
    yield
    # Shutdown
    logger.info("Shutting down CARLA Fuzzing Framework Backend")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="CARLA Scenario Fuzzing Framework",
        description="Backend API for conducting scenario-based fuzzing experiments in CARLA",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(experiments.router, prefix="/api", tags=["experiments"])
    app.include_router(scenarios.router, prefix="/api", tags=["scenarios"])
    app.include_router(configurations.router, prefix="/api", tags=["configurations"])
    app.include_router(results.router, prefix="/api", tags=["results"])
    app.include_router(files.router, prefix="/api", tags=["files"])
    app.include_router(system.router, prefix="/api/system", tags=["system"])
    
    # Include WebSocket routes
    # app.include_router(console_logs.router, prefix="/ws", tags=["websockets"])  # TODO: Fix import path
    
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {"message": "CARLA Scenario Fuzzing Framework Backend"}
    
    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy", "version": "1.0.0"}
    
    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    ) 