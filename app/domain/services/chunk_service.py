"""
ChunkService: business logic for chunks, including embedding validation and version bumping.
"""
from __future__ import annotations

from typing import List, Optional

from app.core.errors import NotFoundError, ValidationError
from app.domain.concurrency.versioning import VersionManager
from app.domain.concurrency.registry import LockRegistry
from app.domain.repositories.libraries import LibraryRepository
from app.domain.repositories.documents import DocumentRepository
from app.domain.repositories.chunks import ChunkRepository
from app.domain.models.chunk import Chunk
from app.domain.services.index_service import IndexService


class ChunkService:
	def __init__(self, libraries: LibraryRepository, documents: DocumentRepository, chunks: ChunkRepository, versions: VersionManager, locks: LockRegistry, indexes: IndexService) -> None:
		self._libraries = libraries
		self._documents = documents
		self._chunks = chunks
		self._versions = versions
		self._locks = locks
		self._indexes = indexes
	
	def _validate_embedding(self, library_id: str, embedding: List[float]) -> None:
		lib = self._libraries.get(library_id)
		if len(embedding) != lib.embedding_dimension:
			raise ValidationError("Embedding dimension does not match library embedding_dimension")
	
	def create(self, library_id: str, document_id: str, text: str, embedding: List[float]) -> Chunk:
		# Validate associations
		self._libraries.get(library_id)
		self._documents.get(document_id)
		# Validate embedding dims
		self._validate_embedding(library_id, embedding)
		lock = self._locks.get_lock(library_id)
		with lock.write_lock():
			chunk = Chunk(library_id=library_id, document_id=document_id, text=text, embedding=embedding)
			self._chunks.create(chunk)
			vi = self._versions.bump_data(library_id)
			# Incrementally update index if present and sync version
			self._indexes.add_chunk(library_id, chunk)
			return chunk
	
	def get(self, chunk_id: str) -> Chunk:
		return self._chunks.get(chunk_id)
	
	def list_by_library(self, library_id: str) -> List[Chunk]:
		self._libraries.get(library_id)
		return self._chunks.list_by_library(library_id)
	
	def list_by_document(self, document_id: str) -> List[Chunk]:
		self._documents.get(document_id)
		return self._chunks.list_by_document(document_id)
	
	def update(self, chunk_id: str, text: Optional[str] = None, embedding: Optional[List[float]] = None) -> Chunk:
		ch = self._chunks.get(chunk_id)
		lock = self._locks.get_lock(ch.library_id)
		with lock.write_lock():
			fields = {}
			if text is not None:
				fields["text"] = text
			if embedding is not None:
				self._validate_embedding(ch.library_id, embedding)
				fields["embedding"] = embedding
			res = self._chunks.update(chunk_id, **fields)
			vi = self._versions.bump_data(ch.library_id)
			# Incremental index update if embedding changed
			if embedding is not None:
				res.embedding = embedding
				self._indexes.update_chunk(ch.library_id, res)
			return res
	
	def delete(self, chunk_id: str) -> None:
		ch = self._chunks.get(chunk_id)
		lock = self._locks.get_lock(ch.library_id)
		with lock.write_lock():
			self._chunks.delete(chunk_id)
			vi = self._versions.bump_data(ch.library_id)
			self._indexes.remove_chunk(ch.library_id, chunk_id)
