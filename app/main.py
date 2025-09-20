"""
Main FastAPI application entry point for Vector DB.
"""
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.settings import settings, NodeRole
from app.core.logging import setup_logging, get_logger
from app.core.errors import register_exception_handlers

from app.api.routers.libraries import router as libraries_router
from app.api.routers.documents import router as documents_router
from app.api.routers.chunks import router as chunks_router
from app.api.routers.query import router as query_router
from app.api.routers.replication import router as replication_router
from app.api.deps import get_persistence_service, get_replication_service


# Initialize logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Application lifespan handler for startup and shutdown events."""
	# Startup
	logger.info(
		"Starting Vector DB API",
		extra={
			"app_name": settings.app_name,
			"version": settings.app_version,
			"environment": settings.environment,
			"host": settings.host,
			"port": settings.port,
			"role": settings.node_role,
		}
	)
	# Load persistence if enabled
	try:
		get_persistence_service().load_all()
	except Exception as e:
		logger.error(f"Persistence load failed: {e}")
	# Start follower replication if configured
	try:
		if settings.node_role == NodeRole.FOLLOWER and settings.leader_url:
			get_replication_service().start()
	except Exception as e:
		logger.error(f"Replication start failed: {e}")
	
	yield
	
	# Shutdown
	logger.info("Shutting down Vector DB API")
	try:
		get_persistence_service().save_all()
	except Exception as e:
		logger.error(f"Persistence save failed: {e}")
	try:
		if settings.node_role == NodeRole.FOLLOWER and settings.leader_url:
			get_replication_service().stop()
	except Exception as e:
		logger.error(f"Replication stop failed: {e}")


# Create FastAPI application
app = FastAPI(
	title=settings.app_name,
	version=settings.app_version,
	description="A REST API for indexing and querying documents in a Vector Database",
	lifespan=lifespan,
	debug=settings.debug,
)

# Register exception handlers
register_exception_handlers(app)

# Add CORS middleware
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],  # Configure appropriately for production
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.get(
	"/health",
	tags=["Health"],
	summary="Health check endpoint",
	response_model=Dict[str, Any],
	status_code=status.HTTP_200_OK,
)
async def health_check() -> Dict[str, Any]:
	"""
	Health check endpoint to verify the API is running.
	
	Returns:
		Dict containing health status and basic system information.
	"""
	return {
		"status": "healthy",
		"app_name": settings.app_name,
		"version": settings.app_version,
		"environment": settings.environment,
		"role": settings.node_role,
	}


@app.get(
	"/",
	tags=["Root"],
	summary="Root endpoint",
	response_model=Dict[str, str],
)
async def root() -> Dict[str, str]:
	"""
	Root endpoint providing basic API information.
	
	Returns:
		Dict with welcome message and API documentation link.
	"""
	return {
		"message": f"Welcome to {settings.app_name}",
		"docs": "/docs",
		"health": "/health",
	}


# Include API routers
app.include_router(libraries_router)
app.include_router(documents_router)
app.include_router(chunks_router)
app.include_router(query_router)
app.include_router(replication_router)


if __name__ == "__main__":
	import uvicorn
	
	uvicorn.run(
		"app.main:app",
		host=settings.host,
		port=settings.port,
		reload=settings.debug,
		log_level=settings.log_level.lower(),
	)
