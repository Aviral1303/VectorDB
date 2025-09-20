"""
In-memory repository for Chunk entities.
"""
from __future__ import annotations

from collections import defaultdict
from threading import RLock
from typing import Dict, List, Set

from app.core.errors import NotFoundError, ConflictError
from app.domain.models.chunk import Chunk


class ChunkRepository:
	"""Thread-safe in-memory repository for chunks."""
	
	def __init__(self) -> None:
		self._items: Dict[str, Chunk] = {}
		self._by_library: Dict[str, Set[str]] = defaultdict(set)
		self._by_document: Dict[str, Set[str]] = defaultdict(set)
		self._lock = RLock()
	
	def create(self, chunk: Chunk) -> Chunk:
		with self._lock:
			if chunk.id in self._items:
				raise ConflictError(f"Chunk with id {chunk.id} already exists")
			self._items[chunk.id] = chunk
			self._by_library[chunk.library_id].add(chunk.id)
			self._by_document[chunk.document_id].add(chunk.id)
			return chunk
	
	def bulk_get(self, ids: List[str]) -> List[Chunk]:
		with self._lock:
			result: List[Chunk] = []
			for cid in ids:
				c = self._items.get(cid)
				if c:
					result.append(c)
			return result
	
	def get(self, chunk_id: str) -> Chunk:
		with self._lock:
			c = self._items.get(chunk_id)
			if not c:
				raise NotFoundError(f"Chunk {chunk_id} not found")
			return c
	
	def list_by_library(self, library_id: str) -> List[Chunk]:
		with self._lock:
			return [self._items[cid] for cid in self._by_library.get(library_id, set())]
	
	def list_by_document(self, document_id: str) -> List[Chunk]:
		with self._lock:
			return [self._items[cid] for cid in self._by_document.get(document_id, set())]
	
	def update(self, chunk_id: str, **fields) -> Chunk:
		with self._lock:
			c = self._items.get(chunk_id)
			if not c:
				raise NotFoundError(f"Chunk {chunk_id} not found")
			for k, v in fields.items():
				if hasattr(c, k) and v is not None:
					setattr(c, k, v)
			c.touch()
			return c
	
	def delete(self, chunk_id: str) -> None:
		with self._lock:
			c = self._items.get(chunk_id)
			if not c:
				raise NotFoundError(f"Chunk {chunk_id} not found")
			del self._items[chunk_id]
			self._by_library[c.library_id].discard(chunk_id)
			self._by_document[c.document_id].discard(chunk_id)
	
	def replace_all(self, chunks: List[Chunk]) -> None:
		with self._lock:
			self._items = {c.id: c for c in chunks}
			self._by_library.clear()
			self._by_document.clear()
			for c in chunks:
				self._by_library[c.library_id].add(c.id)
				self._by_document[c.document_id].add(c.id)
