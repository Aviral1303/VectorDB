"""
Random Hyperplane LSH index for cosine similarity.
Generates R random hyperplanes; hash is the sign pattern (bitstring) of dot(q, plane).
Candidates are retrieved from the matching bucket; if empty, fallback to linear scan.
"""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple
import math
import random

from app.domain.indexes.base import VectorIndex, Vector, normalize, dot, cosine_similarity


class RandomHyperplaneLSHIndex(VectorIndex):
	"""Random Hyperplane LSH for cosine similarity."""
	
	def __init__(self, num_planes: int = 24, seed: int = 42) -> None:
		self._num_planes = num_planes
		self._seed = seed
		self._planes: List[List[float]] = []
		self._buckets: Dict[str, List[str]] = {}
		self._id_to_vec: Dict[str, List[float]] = {}
	
	def _init_planes(self, dim: int) -> None:
		rng = random.Random(self._seed)
		self._planes = []
		for _ in range(self._num_planes):
			# Gaussian random vector via Box-Muller or simple normal approximation
			# Using simple uniform sum approximation
			vec = [rng.gauss(0.0, 1.0) for _ in range(dim)]
			self._planes.append(normalize(vec))
	
	def _hash(self, v: Sequence[float]) -> str:
		bits = []
		for p in self._planes:
			bits.append('1' if dot(v, p) >= 0 else '0')
		return ''.join(bits)
	
	def build(self, vectors: List[Vector], ids: List[str]) -> None:
		self._buckets.clear()
		self._id_to_vec.clear()
		if not vectors:
			self._planes = []
			return
		dim = len(vectors[0])
		self._init_planes(dim)
		for v, id in zip(vectors, ids):
			vn = normalize(v)
			self._id_to_vec[id] = vn
			key = self._hash(vn)
			self._buckets.setdefault(key, []).append(id)
	
	def add(self, vector: Vector, id: str) -> None:
		if id in self._id_to_vec:
			raise ValueError(f"Duplicate id {id}")
		vn = normalize(vector)
		self._id_to_vec[id] = vn
		if not self._planes:
			self._init_planes(len(vn))
		key = self._hash(vn)
		self._buckets.setdefault(key, []).append(id)
	
	def remove(self, id: str) -> None:
		vn = self._id_to_vec.pop(id, None)
		if vn is None:
			raise KeyError(id)
		key = self._hash(vn)
		bucket = self._buckets.get(key, [])
		if id in bucket:
			bucket.remove(id)
			if not bucket:
				del self._buckets[key]
	
	def update(self, id: str, new_vector: Vector) -> None:
		# Remove then add
		self.remove(id)
		self.add(new_vector, id)
	
	def search(self, query: Vector, k: int) -> List[Tuple[str, float]]:
		if k <= 0:
			return []
		if not self._id_to_vec:
			return []
		q = normalize(query)
		candidates: List[str] = []
		if self._planes:
			key = self._hash(q)
			candidates = list(self._buckets.get(key, []))
		# Fallback if bucket empty: linear scan of all ids
		if not candidates:
			candidates = list(self._id_to_vec.keys())
		pairs: List[Tuple[str, float]] = []
		for cid in candidates:
			v = self._id_to_vec[cid]
			score = cosine_similarity(q, v)
			pairs.append((cid, score))
		pairs.sort(key=lambda x: x[1], reverse=True)
		return pairs[:k]
	
	def size(self) -> int:
		return len(self._id_to_vec)
