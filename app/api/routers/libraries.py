"""
Libraries router: CRUD and index endpoints.
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Response

from app.api.schemas import (
	CreateLibraryRequest,
	LibraryResponse,
	UpdateLibraryRequest,
	IndexBuildRequest,
	IndexStatusResponse,
)
from app.core.errors import DomainError, NotFoundError
from app.core.settings import IndexType
from app.api.deps import (
	get_library_service,
	get_document_repository,
	get_chunk_repository,
	get_index_service,
	get_version_manager,
	require_leader,
)
from app.domain.services.library_service import LibraryService


router = APIRouter(prefix="/api/v1/libraries", tags=["Libraries"])


@router.post("", response_model=LibraryResponse, status_code=status.HTTP_201_CREATED)
def create_library(payload: CreateLibraryRequest, _: None = Depends(require_leader), svc: LibraryService = Depends(get_library_service)) -> LibraryResponse:
	lib = svc.create(
		name=payload.name,
		embedding_dimension=payload.embedding_dimension,
		description=payload.description,
		default_index_type=payload.default_index_type,
	)
	return LibraryResponse(
		id=lib.id,
		name=lib.name,
		description=lib.description,
		embedding_dimension=lib.embedding_dimension,
		default_index_type=lib.default_index_type,
	)


@router.get("", response_model=List[LibraryResponse])
def list_libraries(svc: LibraryService = Depends(get_library_service)) -> List[LibraryResponse]:
	libs = svc.list()
	return [
		LibraryResponse(
			id=l.id,
			name=l.name,
			description=l.description,
			embedding_dimension=l.embedding_dimension,
			default_index_type=l.default_index_type,
		)
		for l in libs
	]


@router.get("/{library_id}", response_model=LibraryResponse)
def get_library(library_id: str, svc: LibraryService = Depends(get_library_service)) -> LibraryResponse:
	l = svc.get(library_id)
	return LibraryResponse(
		id=l.id,
		name=l.name,
		description=l.description,
		embedding_dimension=l.embedding_dimension,
		default_index_type=l.default_index_type,
	)


@router.patch("/{library_id}", response_model=LibraryResponse)
def update_library(library_id: str, payload: UpdateLibraryRequest, _: None = Depends(require_leader), svc: LibraryService = Depends(get_library_service)) -> LibraryResponse:
	l = svc.update(library_id, name=payload.name, description=payload.description, default_index_type=payload.default_index_type)
	return LibraryResponse(
		id=l.id,
		name=l.name,
		description=l.description,
		embedding_dimension=l.embedding_dimension,
		default_index_type=l.default_index_type,
	)


@router.delete("/{library_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_library(library_id: str, _: None = Depends(require_leader), svc: LibraryService = Depends(get_library_service)) -> Response:
	svc.delete(library_id, cascade=True)
	return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{library_id}/index:build", status_code=status.HTTP_202_ACCEPTED)
def build_index(library_id: str, payload: IndexBuildRequest, _: None = Depends(require_leader), idx=Depends(get_index_service), chunks=Depends(get_chunk_repository)):
	# Collect chunks for this library
	cs = chunks.list_by_library(library_id)
	idx.build_index_async(library_id, payload.index_type, cs)
	return {"status": "building", "index_type": payload.index_type}


@router.get("/{library_id}/index:status", response_model=IndexStatusResponse)
def index_status(library_id: str, idx=Depends(get_index_service), versions=Depends(get_version_manager)) -> IndexStatusResponse:
	index = idx.get_index(library_id)
	itype = idx.get_index_type(library_id)
	vi = versions.get(library_id)
	return IndexStatusResponse(
		index_type=itype,
		size=index.size() if index else 0,
		data_version=vi.data_version,
		index_version=vi.index_version,
		stale=vi.index_version != vi.data_version,
	)
