"""
LibraryService: business logic for libraries, including cascaded deletes.
"""
from __future__ import annotations

from typing import List, Optional

from app.core.errors import NotFoundError
from app.core.settings import IndexType
from app.domain.repositories.libraries import LibraryRepository
from app.domain.repositories.documents import DocumentRepository
from app.domain.repositories.chunks import ChunkRepository
from app.domain.models.library import Library


class LibraryService:
	def __init__(self, libraries: LibraryRepository, documents: DocumentRepository, chunks: ChunkRepository) -> None:
		self._libraries = libraries
		self._documents = documents
		self._chunks = chunks
	
	def create(self, name: str, embedding_dimension: int, description: Optional[str], default_index_type: IndexType) -> Library:
		lib = Library(name=name, embedding_dimension=embedding_dimension, description=description, default_index_type=default_index_type)
		return self._libraries.create(lib)
	
	def get(self, library_id: str) -> Library:
		return self._libraries.get(library_id)
	
	def list(self) -> List[Library]:
		return self._libraries.list()
	
	def update(self, library_id: str, name: Optional[str] = None, description: Optional[str] = None, default_index_type: Optional[IndexType] = None) -> Library:
		fields = {}
		if name is not None:
			fields["name"] = name
		if description is not None:
			fields["description"] = description
		if default_index_type is not None:
			fields["default_index_type"] = default_index_type
		return self._libraries.update(library_id, **fields)
	
	def delete(self, library_id: str, cascade: bool = True) -> None:
		# Ensure exists
		self._libraries.get(library_id)
		if cascade:
			# Delete chunks under documents of this library
			docs = self._documents.list_by_library(library_id)
			for d in docs:
				for ch in self._chunks.list_by_document(d.id):
					self._chunks.delete(ch.id)
				self._documents.delete(d.id)
		self._libraries.delete(library_id)
