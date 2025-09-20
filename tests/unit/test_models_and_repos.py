import pytest

from app.domain.models.library import Library
from app.domain.models.document import Document
from app.domain.models.chunk import Chunk
from app.domain.repositories.libraries import LibraryRepository
from app.domain.repositories.documents import DocumentRepository
from app.domain.repositories.chunks import ChunkRepository
from app.core.settings import IndexType


def test_library_crud():
	libs = LibraryRepository()
	lib = Library(name="TestLib", embedding_dimension=8, default_index_type=IndexType.BRUTE_FORCE)
	libs.create(lib)
	assert libs.get(lib.id).name == "TestLib"
	libs.update(lib.id, description="demo")
	assert libs.get(lib.id).description == "demo"
	assert len(libs.list()) == 1
	libs.delete(lib.id)
	with pytest.raises(Exception):
		libs.get(lib.id)


def test_document_crud():
	libs = LibraryRepository()
	docs = DocumentRepository()
	lib = Library(name="TestLib", embedding_dimension=8, default_index_type=IndexType.BRUTE_FORCE)
	libs.create(lib)
	doc = Document(library_id=lib.id, title="Doc1")
	docs.create(doc)
	assert docs.get(doc.id).title == "Doc1"
	lst = docs.list_by_library(lib.id)
	assert len(lst) == 1 and lst[0].id == doc.id
	docs.update(doc.id, description="desc")
	assert docs.get(doc.id).description == "desc"
	docs.delete(doc.id)
	with pytest.raises(Exception):
		docs.get(doc.id)


def test_chunk_crud():
	libs = LibraryRepository()
	docs = DocumentRepository()
	chunks = ChunkRepository()
	lib = Library(name="TestLib", embedding_dimension=4, default_index_type=IndexType.BRUTE_FORCE)
	libs.create(lib)
	doc = Document(library_id=lib.id, title="Doc1")
	docs.create(doc)
	ch = Chunk(library_id=lib.id, document_id=doc.id, text="hello", embedding=[0.1, 0.2, 0.3, 0.4])
	chunks.create(ch)
	assert chunks.get(ch.id).text == "hello"
	lst = chunks.list_by_library(lib.id)
	assert len(lst) == 1 and lst[0].id == ch.id
	lst2 = chunks.list_by_document(doc.id)
	assert len(lst2) == 1 and lst2[0].id == ch.id
	chunks.update(ch.id, text="world")
	assert chunks.get(ch.id).text == "world"
	chunks.delete(ch.id)
	with pytest.raises(Exception):
		chunks.get(ch.id)
