"""
In-memory repository for Document entities.
"""
from __future__ import annotations

from collections import defaultdict
from threading import RLock
from typing import Dict, List, Set

from app.core.errors import NotFoundError, ConflictError
from app.domain.models.document import Document


class DocumentRepository:
	"""Thread-safe in-memory repository for documents."""
	
	def __init__(self) -> None:
		self._items: Dict[str, Document] = {}
		self._by_library: Dict[str, Set[str]] = defaultdict(set)
		self._lock = RLock()
	
	def create(self, document: Document) -> Document:
		with self._lock:
			if document.id in self._items:
				raise ConflictError(f"Document with id {document.id} already exists")
			self._items[document.id] = document
			self._by_library[document.library_id].add(document.id)
			return document
	
	def get(self, document_id: str) -> Document:
		with self._lock:
			doc = self._items.get(document_id)
			if not doc:
				raise NotFoundError(f"Document {document_id} not found")
			return doc
	
	def list_by_library(self, library_id: str) -> List[Document]:
		with self._lock:
			return [self._items[doc_id] for doc_id in self._by_library.get(library_id, set())]
	
	def update(self, document_id: str, **fields) -> Document:
		with self._lock:
			doc = self._items.get(document_id)
			if not doc:
				raise NotFoundError(f"Document {document_id} not found")
			for k, v in fields.items():
				if hasattr(doc, k) and v is not None:
					setattr(doc, k, v)
			doc.touch()
			return doc
	
	def delete(self, document_id: str) -> None:
		with self._lock:
			doc = self._items.get(document_id)
			if not doc:
				raise NotFoundError(f"Document {document_id} not found")
			del self._items[document_id]
			self._by_library[doc.library_id].discard(document_id)
	
	def replace_all(self, documents: List[Document]) -> None:
		with self._lock:
			self._items = {d.id: d for d in documents}
			self._by_library.clear()
			for d in documents:
				self._by_library[d.library_id].add(d.id)
