"""
Chunks router: CRUD endpoints and list-by relations.
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, status, Response, HTTPException

from app.api.schemas import ChunkResponse, CreateChunkRequest, UpdateChunkRequest
from app.api.deps import get_chunk_service, get_embedding_service, require_leader
from app.domain.services.chunk_service import ChunkService
from app.domain.services.embedding_service import EmbeddingService


router = APIRouter(prefix="/api/v1/libraries/{library_id}", tags=["Chunks"])


@router.post("/documents/{document_id}/chunks", response_model=ChunkResponse, status_code=status.HTTP_201_CREATED)
def create_chunk(library_id: str, document_id: str, payload: CreateChunkRequest, _: None = Depends(require_leader), svc: ChunkService = Depends(get_chunk_service), embed_svc: EmbeddingService = Depends(get_embedding_service)) -> ChunkResponse:
	embedding = payload.embedding
	if embedding is None and payload.use_embedding_service:
		from app.api.deps import get_library_repository
		lib = get_library_repository().get(library_id)
		embedding = embed_svc.embed_text(payload.text, lib.embedding_dimension)
	elif embedding is None and not payload.use_embedding_service:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Embedding required unless use_embedding_service=true")
	c = svc.create(library_id, document_id, text=payload.text, embedding=embedding)
	return ChunkResponse(id=c.id, library_id=c.library_id, document_id=c.document_id, text=c.text)


@router.get("/chunks", response_model=List[ChunkResponse])
def list_chunks_by_library(library_id: str, svc: ChunkService = Depends(get_chunk_service)) -> List[ChunkResponse]:
	cs = svc.list_by_library(library_id)
	return [ChunkResponse(id=c.id, library_id=c.library_id, document_id=c.document_id, text=c.text) for c in cs]


@router.get("/documents/{document_id}/chunks", response_model=List[ChunkResponse])
def list_chunks_by_document(library_id: str, document_id: str, svc: ChunkService = Depends(get_chunk_service)) -> List[ChunkResponse]:
	cs = svc.list_by_document(document_id)
	return [ChunkResponse(id=c.id, library_id=c.library_id, document_id=c.document_id, text=c.text) for c in cs]


@router.get("/chunks/{chunk_id}", response_model=ChunkResponse)
def get_chunk(library_id: str, chunk_id: str, svc: ChunkService = Depends(get_chunk_service)) -> ChunkResponse:
	c = svc.get(chunk_id)
	return ChunkResponse(id=c.id, library_id=c.library_id, document_id=c.document_id, text=c.text)


@router.patch("/chunks/{chunk_id}", response_model=ChunkResponse)
def update_chunk(library_id: str, chunk_id: str, payload: UpdateChunkRequest, _: None = Depends(require_leader), svc: ChunkService = Depends(get_chunk_service)) -> ChunkResponse:
	c = svc.update(chunk_id, text=payload.text, embedding=payload.embedding)
	return ChunkResponse(id=c.id, library_id=c.library_id, document_id=c.document_id, text=c.text)


@router.delete("/chunks/{chunk_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_chunk(library_id: str, chunk_id: str, _: None = Depends(require_leader), svc: ChunkService = Depends(get_chunk_service)) -> Response:
	svc.delete(chunk_id)
	return Response(status_code=status.HTTP_204_NO_CONTENT)
