"""
Vector index base interfaces and utilities.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List, Sequence, Tuple
import math


Vector = Sequence[float]


def dot(a: Vector, b: Vector) -> float:
	return sum(x * y for x, y in zip(a, b))


def l2_norm(a: Vector) -> float:
	return math.sqrt(sum(x * x for x in a))


def normalize(a: Vector) -> List[float]:
	n = l2_norm(a)
	if n == 0:
		return [0.0 for _ in a]
	return [x / n for x in a]


def cosine_similarity(a: Vector, b: Vector) -> float:
	na = l2_norm(a)
	nb = l2_norm(b)
	if na == 0 or nb == 0:
		return 0.0
	return dot(a, b) / (na * nb)


class VectorIndex(ABC):
	"""Abstract base class for vector indexes."""
	
	@abstractmethod
	def build(self, vectors: List[Vector], ids: List[str]) -> None:
		...
	
	@abstractmethod
	def add(self, vector: Vector, id: str) -> None:
		...
	
	@abstractmethod
	def remove(self, id: str) -> None:
		...
	
	@abstractmethod
	def update(self, id: str, new_vector: Vector) -> None:
		...
	
	@abstractmethod
	def search(self, query: Vector, k: int) -> List[Tuple[str, float]]:
		"""Return top-k pairs (id, score) with higher score = more similar."""
		...
	
	@abstractmethod
	def size(self) -> int:
		...
