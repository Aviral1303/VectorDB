"""
Lock registry for per-library RWLocks.
"""
from __future__ import annotations

from threading import RLock
from typing import Dict

from app.domain.concurrency.rwlock import RWLock


class LockRegistry:
	"""Thread-safe registry mapping library_id to RWLock."""
	
	def __init__(self) -> None:
		self._locks: Dict[str, RWLock] = {}
		self._lock = RLock()
	
	def get_lock(self, library_id: str) -> RWLock:
		with self._lock:
			lock = self._locks.get(library_id)
			if lock is None:
				lock = RWLock()
				self._locks[library_id] = lock
			return lock
