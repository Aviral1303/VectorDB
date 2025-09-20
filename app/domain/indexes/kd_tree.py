"""
KD-Tree index implementation for Euclidean distance on normalized vectors.
Note: Works best for low dimensions; vectors should be normalized for cosine equivalence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple
import math

from app.domain.indexes.base import VectorIndex, Vector, l2_norm, normalize


@dataclass
class _Node:
	point: List[float]
	id: str
	axis: int
	left: Optional["_Node"]
	right: Optional["_Node"]


def _distance_sq(a: Sequence[float], b: Sequence[float]) -> float:
	return sum((x - y) * (x - y) for x, y in zip(a, b))


class KDTreeIndex(VectorIndex):
	"""KD-Tree for exact kNN on L2 distance (with normalized vectors)."""
	
	def __init__(self) -> None:
		self._root: Optional[_Node] = None
		self._size: int = 0
		self._dim: int = 0
		self._id_to_point: dict[str, List[float]] = {}
	
	def build(self, vectors: List[Vector], ids: List[str]) -> None:
		if not vectors:
			self._root = None
			self._size = 0
			self._dim = 0
			self._id_to_point = {}
			return
		points = [normalize(v) for v in vectors]
		self._dim = len(points[0])
		items = list(zip(points, ids))
		self._root = self._build_recursive(items, depth=0)
		self._size = len(items)
		self._id_to_point = {i: p for p, i in items}
	
	def _build_recursive(self, items: List[Tuple[List[float], str]], depth: int) -> Optional[_Node]:
		if not items:
			return None
		axis = depth % len(items[0][0])
		items.sort(key=lambda x: x[0][axis])
		mid = len(items) // 2
		point, pid = items[mid]
		node = _Node(point=point, id=pid, axis=axis, left=None, right=None)
		node.left = self._build_recursive(items[:mid], depth + 1)
		node.right = self._build_recursive(items[mid + 1 :], depth + 1)
		return node
	
	def add(self, vector: Vector, id: str) -> None:
		# For simplicity, rebuild with inserted element (keeps code short and deterministic)
		all_ids = list(self._id_to_point.keys()) + [id]
		all_points = list(self._id_to_point.values()) + [normalize(vector)]
		self.build(all_points, all_ids)
	
	def remove(self, id: str) -> None:
		if id not in self._id_to_point:
			raise KeyError(id)
		all_ids = [i for i in self._id_to_point.keys() if i != id]
		all_points = [self._id_to_point[i] for i in all_ids]
		self.build(all_points, all_ids)
	
	def update(self, id: str, new_vector: Vector) -> None:
		if id not in self._id_to_point:
			raise KeyError(id)
		self._id_to_point[id] = normalize(new_vector)
		all_ids = list(self._id_to_point.keys())
		all_points = [self._id_to_point[i] for i in all_ids]
		self.build(all_points, all_ids)
	
	def search(self, query: Vector, k: int) -> List[Tuple[str, float]]:
		if not self._root or k <= 0:
			return []
		q = normalize(query)
		best: List[Tuple[float, str]] = []  # max-heap via negative distance? simpler: list sorted later
		# We will maintain a list and trim; for small k this is fine.
		self._search_node(self._root, q, k, best)
		best.sort(key=lambda x: x[0])
		# Convert distance to cosine similarity (since vectors are normalized): sim = 1 - d^2/2
		results: List[Tuple[str, float]] = []
		for dist_sq, pid in best[:k]:
			cos_sim = 1.0 - (dist_sq / 2.0)
			results.append((pid, cos_sim))
		return results
	
	def _search_node(self, node: Optional[_Node], q: List[float], k: int, best: List[Tuple[float, str]]):
		if node is None:
			return
		dist_sq = _distance_sq(q, node.point)
		best.append((dist_sq, node.id))
		best.sort(key=lambda x: x[0])
		if len(best) > k:
			best.pop()  # remove worst
		axis = node.axis
		delta = q[axis] - node.point[axis]
		first = node.left if delta < 0 else node.right
		second = node.right if delta < 0 else node.left
		self._search_node(first, q, k, best)
		# Check whether we need to explore the other branch
		if len(best) < k or (delta * delta) < best[-1][0]:
			self._search_node(second, q, k, best)
	
	def size(self) -> int:
		return self._size
