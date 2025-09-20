"""
In-memory repository for Library entities.
"""
from __future__ import annotations

from threading import RLock
from typing import Dict, List, Optional

from app.core.errors import NotFoundError, ConflictError
from app.domain.models.library import Library


class LibraryRepository:
	"""Thread-safe in-memory repository for libraries."""
	
	def __init__(self) -> None:
		self._items: Dict[str, Library] = {}
		self._lock = RLock()
	
	def create(self, library: Library) -> Library:
		with self._lock:
			if library.id in self._items:
				raise ConflictError(f"Library with id {library.id} already exists")
			self._items[library.id] = library
			return library
	
	def get(self, library_id: str) -> Library:
		with self._lock:
			lib = self._items.get(library_id)
			if not lib:
				raise NotFoundError(f"Library {library_id} not found")
			return lib
	
	def list(self) -> List[Library]:
		with self._lock:
			return list(self._items.values())
	
	def update(self, library_id: str, **fields) -> Library:
		with self._lock:
			lib = self._items.get(library_id)
			if not lib:
				raise NotFoundError(f"Library {library_id} not found")
			for k, v in fields.items():
				if hasattr(lib, k) and v is not None:
					setattr(lib, k, v)
			lib.touch()
			return lib
	
	def delete(self, library_id: str) -> None:
		with self._lock:
			if library_id not in self._items:
				raise NotFoundError(f"Library {library_id} not found")
			del self._items[library_id]
	
	def replace_all(self, libraries: List[Library]) -> None:
		with self._lock:
			self._items = {l.id: l for l in libraries}
