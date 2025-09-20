"""
ReplicationService: follower polls leader snapshot and applies it locally.
"""
from __future__ import annotations

import threading
import time
from typing import List

import httpx

from app.core.settings import settings, NodeRole
from app.domain.models.library import Library
from app.domain.models.document import Document
from app.domain.models.chunk import Chunk
from app.domain.repositories.libraries import LibraryRepository
from app.domain.repositories.documents import DocumentRepository
from app.domain.repositories.chunks import ChunkRepository
from app.domain.services.index_service import IndexService


class ReplicationService:
	def __init__(self, libs: LibraryRepository, docs: DocumentRepository, chunks: ChunkRepository, index: IndexService) -> None:
		self._libs = libs
		self._docs = docs
		self._chunks = chunks
		self._index = index
		self._thread: threading.Thread | None = None
		self._stop = threading.Event()
	
	def start(self) -> None:
		if settings.node_role != NodeRole.FOLLOWER or not settings.leader_url:
			return
		if self._thread and self._thread.is_alive():
			return
		self._stop.clear()
		self._thread = threading.Thread(target=self._run, daemon=True)
		self._thread.start()
	
	def stop(self) -> None:
		self._stop.set()
		if self._thread:
			self._thread.join(timeout=1.0)
	
	def _run(self) -> None:
		while not self._stop.is_set():
			try:
				self._replicate_once()
			except Exception:
				pass
			time.sleep(max(1, settings.replication_interval_seconds))
	
	def _replicate_once(self) -> None:
		leader = settings.leader_url.rstrip("/")
		with httpx.Client(timeout=20.0) as client:
			r = client.get(f"{leader}/api/v1/replication/snapshot")
			r.raise_for_status()
			s = r.json()
			libraries = [Library(**d) for d in s.get("libraries", [])]
			documents = [Document(**d) for d in s.get("documents", [])]
			chunks = [Chunk(**d) for d in s.get("chunks", [])]
			# Replace repositories wholesale
			self._libs.replace_all(libraries)
			self._docs.replace_all(documents)
			self._chunks.replace_all(chunks)
			# Rebuild indexes per library using current selected types
			for lib in libraries:
				cs = self._chunks.list_by_library(lib.id)
				self._index.build_index(lib.id, lib.default_index_type, cs)
