"""
PersistenceService: JSON snapshot load/save for in-memory repositories.
"""
from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Dict, List

from app.core.settings import settings
from app.domain.repositories.libraries import LibraryRepository
from app.domain.repositories.documents import DocumentRepository
from app.domain.repositories.chunks import ChunkRepository
from app.domain.models.library import Library
from app.domain.models.document import Document
from app.domain.models.chunk import Chunk


class PersistenceService:
	"""Persist repositories to disk as JSON and load them on startup.
	
	Files:
	- libraries.json
	- documents.json
	- chunks.json
	"""
	def __init__(self, libs: LibraryRepository, docs: DocumentRepository, chunks: ChunkRepository) -> None:
		self._libs = libs
		self._docs = docs
		self._chunks = chunks
		self._dir = settings.persistence_dir
	
	def load_all(self) -> None:
		if not settings.persistence_enabled:
			return
		os.makedirs(self._dir, exist_ok=True)
		# Libraries
		libs_path = os.path.join(self._dir, "libraries.json")
		if os.path.exists(libs_path):
			with open(libs_path, "r", encoding="utf-8") as f:
				data = json.load(f)
				for item in data:
					lib = Library(**item)
					self._libs.create(lib)
		# Documents
		docs_path = os.path.join(self._dir, "documents.json")
		if os.path.exists(docs_path):
			with open(docs_path, "r", encoding="utf-8") as f:
				data = json.load(f)
				for item in data:
					doc = Document(**item)
					self._docs.create(doc)
		# Chunks
		chunks_path = os.path.join(self._dir, "chunks.json")
		if os.path.exists(chunks_path):
			with open(chunks_path, "r", encoding="utf-8") as f:
				data = json.load(f)
				for item in data:
					chunk = Chunk(**item)
					self._chunks.create(chunk)
	
	def save_all(self) -> None:
		if not settings.persistence_enabled:
			return
		os.makedirs(self._dir, exist_ok=True)
		# Serialize repositories
		libs = [l.model_dump() for l in self._libs.list()]
		# For documents and chunks, gather across all
		# We don't have list_all; derive by listing per library
		docs: List[Dict[str, Any]] = []
		chunks: List[Dict[str, Any]] = []
		for lib in self._libs.list():
			for d in self._docs.list_by_library(lib.id):
				docs.append(d.model_dump())
			for c in self._chunks.list_by_library(lib.id):
				chunks.append(c.model_dump())
		self._atomic_write_json(os.path.join(self._dir, "libraries.json"), libs)
		self._atomic_write_json(os.path.join(self._dir, "documents.json"), docs)
		self._atomic_write_json(os.path.join(self._dir, "chunks.json"), chunks)
	
	def _atomic_write_json(self, path: str, data: Any) -> None:
		dirname = os.path.dirname(path)
		os.makedirs(dirname, exist_ok=True)
		fd, tmp_path = tempfile.mkstemp(dir=dirname, prefix=".tmp_", suffix=".json")
		try:
			with os.fdopen(fd, "w", encoding="utf-8") as f:
				json.dump(data, f, ensure_ascii=False)
			os.replace(tmp_path, path)
		finally:
			try:
				if os.path.exists(tmp_path):
					os.remove(tmp_path)
			except Exception:
				pass
