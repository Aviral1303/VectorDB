"""
IndexService: manages per-library vector indexes, builds, and version sync.
"""
from __future__ import annotations

import threading
from typing import Dict, List, Tuple

from app.core.settings import IndexType
from app.domain.concurrency.registry import LockRegistry
from app.domain.concurrency.versioning import VersionManager
from app.domain.indexes.base import VectorIndex
from app.domain.indexes.brute_force import BruteForceIndex
from app.domain.indexes.kd_tree import KDTreeIndex
from app.domain.indexes.lsh import RandomHyperplaneLSHIndex
from app.domain.models.chunk import Chunk


class IndexService:
	"""Service to manage vector indexes per library."""
	
	def __init__(self, lock_registry: LockRegistry, version_manager: VersionManager) -> None:
		self._lock_registry = lock_registry
		self._version_manager = version_manager
		self._indexes: Dict[str, VectorIndex] = {}
		self._index_types: Dict[str, IndexType] = {}
		self._building: Dict[str, bool] = {}
	
	def build_index(self, library_id: str, index_type: IndexType, chunks: List[Chunk]) -> None:
		lock = self._lock_registry.get_lock(library_id)
		with lock.read_lock():
			vectors = [c.embedding for c in chunks]
			ids = [c.id for c in chunks]
		# Build off-lock
		index = self._create_index(index_type)
		index.build(vectors, ids)
		# Swap under write lock and sync version
		with lock.write_lock():
			self._indexes[library_id] = index
			self._index_types[library_id] = index_type
			vi = self._version_manager.get(library_id)
			self._version_manager.set_index_version(library_id, vi.data_version)
			self._building[library_id] = False
	
	def build_index_async(self, library_id: str, index_type: IndexType, chunks: List[Chunk]) -> None:
		if self._building.get(library_id):
			return
		self._building[library_id] = True
		threading.Thread(target=self.build_index, args=(library_id, index_type, chunks), daemon=True).start()
	
	def rebuild_async_using_existing_type(self, library_id: str, chunks: List[Chunk]) -> None:
		itype = self._index_types.get(library_id, IndexType.BRUTE_FORCE)
		self.build_index_async(library_id, itype, chunks)
	
	def is_building(self, library_id: str) -> bool:
		return self._building.get(library_id, False)
	
	def get_index(self, library_id: str) -> VectorIndex | None:
		return self._indexes.get(library_id)
	
	def get_index_type(self, library_id: str) -> IndexType | None:
		return self._index_types.get(library_id)
	
	def add_chunk(self, library_id: str, chunk: Chunk) -> None:
		idx = self._indexes.get(library_id)
		if idx is not None:
			idx.add(chunk.embedding, chunk.id)
			# Keep index version in sync with data since we've incrementally updated the index
			vi = self._version_manager.get(library_id)
			self._version_manager.set_index_version(library_id, vi.data_version)
	
	def remove_chunk(self, library_id: str, chunk_id: str) -> None:
		idx = self._indexes.get(library_id)
		if idx is not None:
			idx.remove(chunk_id)
			vi = self._version_manager.get(library_id)
			self._version_manager.set_index_version(library_id, vi.data_version)
	
	def update_chunk(self, library_id: str, chunk: Chunk) -> None:
		idx = self._indexes.get(library_id)
		if idx is not None:
			idx.update(chunk.id, chunk.embedding)
			vi = self._version_manager.get(library_id)
			self._version_manager.set_index_version(library_id, vi.data_version)
	
	def search(self, library_id: str, query: List[float], k: int) -> List[Tuple[str, float]]:
		idx = self._indexes.get(library_id)
		if idx is None:
			return []
		return idx.search(query, k)
	
	def _create_index(self, index_type: IndexType) -> VectorIndex:
		if index_type == IndexType.BRUTE_FORCE:
			return BruteForceIndex(pre_normalize=True)
		if index_type == IndexType.KD_TREE:
			return KDTreeIndex()
		if index_type == IndexType.LSH:
			return RandomHyperplaneLSHIndex(num_planes=24)
		raise NotImplementedError(f"Index type {index_type} not implemented yet")
