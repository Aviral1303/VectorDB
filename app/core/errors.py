"""
Core error types for domain and repository layers and exception handlers.
"""
from fastapi import FastAPI, HTTPException, status


class DomainError(Exception):
	"""Base class for domain-level errors."""


class NotFoundError(DomainError):
	"""Raised when an entity is not found."""


class ConflictError(DomainError):
	"""Raised when a conflict occurs (e.g., duplicate IDs)."""


class ValidationError(DomainError):
	"""Raised when validation fails at the domain/repository layer."""


def register_exception_handlers(app: FastAPI) -> None:
	@app.exception_handler(NotFoundError)
	async def handle_not_found(_, exc: NotFoundError):
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
	
	@app.exception_handler(ConflictError)
	async def handle_conflict(_, exc: ConflictError):
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
	
	@app.exception_handler(ValidationError)
	async def handle_validation(_, exc: ValidationError):
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
