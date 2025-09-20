"""
Version management for libraries and indexes.
"""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Dict


@dataclass
class VersionInfo:
	data_version: int = 0
	index_version: int = -1  # -1 means no index built yet


class VersionManager:
	"""Thread-safe version manager per library."""
	
	def __init__(self) -> None:
		self._versions: Dict[str, VersionInfo] = {}
		self._lock = RLock()
	
	def get(self, library_id: str) -> VersionInfo:
		with self._lock:
			return self._versions.setdefault(library_id, VersionInfo())
	
	def bump_data(self, library_id: str) -> VersionInfo:
		with self._lock:
			vi = self._versions.setdefault(library_id, VersionInfo())
			vi.data_version += 1
			return vi
	
	def set_index_version(self, library_id: str, version: int) -> VersionInfo:
		with self._lock:
			vi = self._versions.setdefault(library_id, VersionInfo())
			vi.index_version = version
			return vi
	
	def is_index_stale(self, library_id: str) -> bool:
		with self._lock:
			vi = self._versions.setdefault(library_id, VersionInfo())
			return vi.index_version != vi.data_version
