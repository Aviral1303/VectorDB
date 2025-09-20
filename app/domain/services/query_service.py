"""
QueryService: performs kNN searches against a library's index.
"""
from __future__ import annotations

from typing import List, Tuple, Optional
from datetime import datetime

from app.core.settings import settings
from app.domain.concurrency.registry import LockRegistry
from app.domain.concurrency.versioning import VersionManager
from app.domain.repositories.chunks import ChunkRepository
from app.domain.services.index_service import IndexService
from app.domain.models.chunk import Chunk


class QueryService:
	"""Service to execute kNN queries with policy for stale indexes and optional filtering."""
	
	def __init__(self, lock_registry: LockRegistry, version_manager: VersionManager, chunks_repo: ChunkRepository, index_service: IndexService) -> None:
		self._locks = lock_registry
		self._versions = version_manager
		self._chunks = chunks_repo
		self._index_service = index_service
	
	def knn(self, library_id: str, query_embedding: List[float], k: int, filter_dto: Optional[dict] = None) -> List[Tuple[str, float]]:
		lock = self._locks.get_lock(library_id)
		with lock.read_lock():
			# If filters present, perform filtered brute-force for correctness
			if filter_dto:
				from app.domain.indexes.brute_force import BruteForceIndex
				chunks = self._chunks.list_by_library(library_id)
				# Apply metadata/text filters first
				filtered = [c for c in chunks if self._matches_filter(c, filter_dto)]
				bf = BruteForceIndex(pre_normalize=True)
				bf.build([c.embedding for c in filtered], [c.id for c in filtered])
				return bf.search(query_embedding, k)
			# Check index freshness and rebuild policy
			stale = self._versions.is_index_stale(library_id)
			if stale:
				cs = self._chunks.list_by_library(library_id)
				self._index_service.rebuild_async_using_existing_type(library_id, cs)
				if not settings.allow_stale_index:
					from app.domain.indexes.brute_force import BruteForceIndex
					bf = BruteForceIndex(pre_normalize=True)
					bf.build([c.embedding for c in cs], [c.id for c in cs])
					return bf.search(query_embedding, k)
			# Use current index
			return self._index_service.search(library_id, query_embedding, k)
	
	def _matches_filter(self, c: Chunk, f: dict) -> bool:
		# text_contains
		text_contains = (f.get("text_contains") or "").strip().lower()
		if text_contains and text_contains not in c.text.lower():
			return False
		# created_at range
		fmt_from = f.get("created_at_from")
		fmt_to = f.get("created_at_to")
		if fmt_from:
			try:
				dfrom = datetime.fromisoformat(fmt_from)
				if c.created_at < dfrom:
					return False
			except Exception:
				pass
		if fmt_to:
			try:
				dto = datetime.fromisoformat(fmt_to)
				if c.created_at > dto:
					return False
			except Exception:
				pass
		# tags_any, tags_all, author_in (if metadata present)
		meta = c.metadata
		tags_any = f.get("tags_any") or []
		tags_all = f.get("tags_all") or []
		author_in = f.get("author_in") or []
		if tags_any and not any(t in (meta.tags or []) for t in tags_any):
			return False
		if tags_all and not all(t in (meta.tags or []) for t in tags_all):
			return False
		if author_in and (meta.author not in author_in):
			return False
		return True
