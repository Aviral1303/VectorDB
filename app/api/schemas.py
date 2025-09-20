"""
API request/response schemas (DTOs) for endpoints.
"""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field

from app.core.settings import IndexType


# Libraries
class CreateLibraryRequest(BaseModel):
	name: str = Field(..., min_length=1)
	description: Optional[str] = None
	embedding_dimension: int = Field(..., gt=0, le=4096)
	default_index_type: IndexType = Field(default=IndexType.BRUTE_FORCE)


class UpdateLibraryRequest(BaseModel):
	name: Optional[str] = None
	description: Optional[str] = None
	default_index_type: Optional[IndexType] = None


class LibraryResponse(BaseModel):
	id: str
	name: str
	description: Optional[str]
	embedding_dimension: int
	default_index_type: IndexType


class IndexBuildRequest(BaseModel):
	index_type: IndexType = Field(default=IndexType.BRUTE_FORCE)


class IndexStatusResponse(BaseModel):
	index_type: Optional[IndexType]
	size: int
	data_version: int
	index_version: int
	stale: bool


# Documents
class CreateDocumentRequest(BaseModel):
	title: str
	description: Optional[str] = None


class UpdateDocumentRequest(BaseModel):
	title: Optional[str] = None
	description: Optional[str] = None


class DocumentResponse(BaseModel):
	id: str
	library_id: str
	title: str
	description: Optional[str]


# Chunks
class CreateChunkRequest(BaseModel):
	text: str
	embedding: Optional[List[float]] = None
	use_embedding_service: bool = Field(default=False)


class UpdateChunkRequest(BaseModel):
	text: Optional[str] = None
	embedding: Optional[List[float]] = None


class ChunkResponse(BaseModel):
	id: str
	library_id: str
	document_id: str
	text: str


# Query
class QueryFilter(BaseModel):
	tags_any: Optional[List[str]] = None
	tags_all: Optional[List[str]] = None
	author_in: Optional[List[str]] = None
	created_at_from: Optional[str] = None
	created_at_to: Optional[str] = None
	text_contains: Optional[str] = None


class QueryRequest(BaseModel):
	query_embedding: Optional[List[float]] = None
	query_text: Optional[str] = None
	k: int = Field(default=5, gt=0)
	use_embedding_service: bool = Field(default=False)
	filter: Optional[QueryFilter] = None


class QueryResult(BaseModel):
	chunk_id: str
	document_id: str
	score: float
	text: str
