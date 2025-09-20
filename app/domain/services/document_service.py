"""
DocumentService: business logic for documents within a library.
"""
from __future__ import annotations

from typing import List, Optional

from app.core.errors import NotFoundError
from app.domain.repositories.documents import DocumentRepository
from app.domain.repositories.libraries import LibraryRepository
from app.domain.models.document import Document


class DocumentService:
	def __init__(self, libraries: LibraryRepository, documents: DocumentRepository) -> None:
		self._libraries = libraries
		self._documents = documents
	
	def create(self, library_id: str, title: str, description: Optional[str] = None) -> Document:
		# Validate library exists
		self._libraries.get(library_id)
		doc = Document(library_id=library_id, title=title, description=description)
		return self._documents.create(doc)
	
	def get(self, document_id: str) -> Document:
		return self._documents.get(document_id)
	
	def list_by_library(self, library_id: str) -> List[Document]:
		# Validate library exists
		self._libraries.get(library_id)
		return self._documents.list_by_library(library_id)
	
	def update(self, document_id: str, title: Optional[str] = None, description: Optional[str] = None) -> Document:
		fields = {}
		if title is not None:
			fields["title"] = title
		if description is not None:
			fields["description"] = description
		return self._documents.update(document_id, **fields)
	
	def delete(self, document_id: str) -> None:
		self._documents.delete(document_id)
