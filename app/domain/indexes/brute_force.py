"""
Brute force vector index implementation using cosine similarity.
"""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from app.domain.indexes.base import VectorIndex, Vector, cosine_similarity, normalize


class BruteForceIndex(VectorIndex):
	"""A simple in-memory flat index scanning all vectors for search."""
	
	def __init__(self, pre_normalize: bool = True) -> None:
		self._vectors: List[List[float]] = []
		self._ids: List[str] = []
		self._pos: Dict[str, int] = {}
		self._pre_normalize = pre_normalize
	
	def build(self, vectors: List[Vector], ids: List[str]) -> None:
		self._vectors = [list(v) for v in vectors]
		if self._pre_normalize:
			self._vectors = [normalize(v) for v in self._vectors]
		self._ids = list(ids)
		self._pos = {id: i for i, id in enumerate(self._ids)}
	
	def add(self, vector: Vector, id: str) -> None:
		if id in self._pos:
			raise ValueError(f"Duplicate id {id}")
		v = list(vector)
		if self._pre_normalize:
			v = normalize(v)
		self._pos[id] = len(self._ids)
		self._ids.append(id)
		self._vectors.append(v)
	
	def remove(self, id: str) -> None:
		idx = self._pos.get(id)
		if idx is None:
			raise KeyError(id)
		last_idx = len(self._ids) - 1
		if idx != last_idx:
			# swap with last
			self._ids[idx], self._ids[last_idx] = self._ids[last_idx], self._ids[idx]
			self._vectors[idx], self._vectors[last_idx] = self._vectors[last_idx], self._vectors[idx]
			self._pos[self._ids[idx]] = idx
		# remove last
		self._ids.pop()
		self._vectors.pop()
		del self._pos[id]
	
	def update(self, id: str, new_vector: Vector) -> None:
		idx = self._pos.get(id)
		if idx is None:
			raise KeyError(id)
		v = list(new_vector)
		if self._pre_normalize:
			v = normalize(v)
		self._vectors[idx] = v
	
	def search(self, query: Vector, k: int) -> List[Tuple[str, float]]:
		q = list(query)
		if self._pre_normalize:
			q = normalize(q)
		pairs: List[Tuple[str, float]] = []
		for id, v in zip(self._ids, self._vectors):
			score = cosine_similarity(q, v)
			pairs.append((id, score))
		pairs.sort(key=lambda x: x[1], reverse=True)
		return pairs[: max(0, k)]
	
	def size(self) -> int:
		return len(self._ids)
