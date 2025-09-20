"""
FastAPI dependency providers for repositories and services.
"""
from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException, status

from app.core.settings import settings, NodeRole
from app.domain.concurrency.registry import LockRegistry
from app.domain.concurrency.versioning import VersionManager
from app.domain.repositories.chunks import ChunkRepository
from app.domain.repositories.documents import DocumentRepository
from app.domain.repositories.libraries import LibraryRepository
from app.domain.services.chunk_service import ChunkService
from app.domain.services.document_service import DocumentService
from app.domain.services.index_service import IndexService
from app.domain.services.library_service import LibraryService
from app.domain.services.query_service import QueryService
from app.domain.services.embedding_service import EmbeddingService
from app.domain.services.persistence_service import PersistenceService
from app.domain.services.replication_service import ReplicationService


def require_leader() -> None:
	if settings.node_role != NodeRole.LEADER:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Writes allowed only on leader")


@lru_cache(maxsize=1)
def get_lock_registry() -> LockRegistry:
	return LockRegistry()


@lru_cache(maxsize=1)
def get_version_manager() -> VersionManager:
	return VersionManager()


@lru_cache(maxsize=1)
def get_library_repository() -> LibraryRepository:
	return LibraryRepository()


@lru_cache(maxsize=1)
def get_document_repository() -> DocumentRepository:
	return DocumentRepository()


@lru_cache(maxsize=1)
def get_chunk_repository() -> ChunkRepository:
	return ChunkRepository()


@lru_cache(maxsize=1)
def get_library_service() -> LibraryService:
	return LibraryService(get_library_repository(), get_document_repository(), get_chunk_repository())


@lru_cache(maxsize=1)
def get_document_service() -> DocumentService:
	return DocumentService(get_library_repository(), get_document_repository())


@lru_cache(maxsize=1)
def get_index_service() -> IndexService:
	return IndexService(get_lock_registry(), get_version_manager())


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
	return EmbeddingService()


@lru_cache(maxsize=1)
def get_persistence_service() -> PersistenceService:
	return PersistenceService(get_library_repository(), get_document_repository(), get_chunk_repository())


@lru_cache(maxsize=1)
def get_replication_service() -> ReplicationService:
	return ReplicationService(get_library_repository(), get_document_repository(), get_chunk_repository(), get_index_service())


@lru_cache(maxsize=1)
def get_chunk_service() -> ChunkService:
	return ChunkService(
		get_library_repository(),
		get_document_repository(),
		get_chunk_repository(),
		get_version_manager(),
		get_lock_registry(),
		get_index_service(),
	)


@lru_cache(maxsize=1)
def get_query_service() -> QueryService:
	return QueryService(get_lock_registry(), get_version_manager(), get_chunk_repository(), get_index_service())
