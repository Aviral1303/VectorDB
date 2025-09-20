"""
Query router: kNN search endpoints.
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas import QueryRequest, QueryResult
from app.api.deps import get_query_service, get_chunk_repository, get_embedding_service, get_library_repository
from app.domain.services.query_service import QueryService
from app.domain.repositories.chunks import ChunkRepository
from app.domain.services.embedding_service import EmbeddingService
from app.domain.repositories.libraries import LibraryRepository


router = APIRouter(prefix="/api/v1/libraries/{library_id}", tags=["Query"])


@router.post("/query", response_model=List[QueryResult])
def query_knn(library_id: str, payload: QueryRequest, svc: QueryService = Depends(get_query_service), chunks_repo: ChunkRepository = Depends(get_chunk_repository), embed_svc: EmbeddingService = Depends(get_embedding_service), libs: LibraryRepository = Depends(get_library_repository)) -> List[QueryResult]:
	if payload.query_embedding is None:
		if not payload.use_embedding_service or payload.query_text is None:
			raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide query_embedding or set use_embedding_service=true with query_text")
		lib = libs.get(library_id)
		query_embedding = embed_svc.embed_text(payload.query_text, lib.embedding_dimension)
	else:
		query_embedding = payload.query_embedding
	pairs = svc.knn(library_id, query_embedding, payload.k, filter_dto=payload.filter.model_dump() if payload.filter else None)
	# Hydrate text and document_id
	by_id = {c.id: c for c in chunks_repo.list_by_library(library_id)}
	results: List[QueryResult] = []
	for cid, score in pairs:
		c = by_id.get(cid)
		if c:
			results.append(QueryResult(chunk_id=cid, document_id=c.document_id, score=score, text=c.text))
	return results
