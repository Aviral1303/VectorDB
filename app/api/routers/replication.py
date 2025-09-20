"""
Replication endpoints for leader-follower architecture.
"""
from __future__ import annotations

from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.settings import settings, NodeRole
from app.api.deps import get_library_repository, get_document_repository, get_chunk_repository, get_index_service
from app.domain.repositories.libraries import LibraryRepository
from app.domain.repositories.documents import DocumentRepository
from app.domain.repositories.chunks import ChunkRepository
from app.domain.services.index_service import IndexService


router = APIRouter(prefix="/api/v1/replication", tags=["Replication"])


@router.get("/snapshot", response_model=Dict[str, Any])
def get_snapshot(libs: LibraryRepository = Depends(get_library_repository), docs: DocumentRepository = Depends(get_document_repository), chunks: ChunkRepository = Depends(get_chunk_repository)) -> Dict[str, Any]:
	if settings.node_role != NodeRole.LEADER:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Snapshot only available on leader")
	libraries = [l.model_dump() for l in libs.list()]
	documents = []
	chunks_out = []
	for l in libs.list():
		for d in docs.list_by_library(l.id):
			documents.append(d.model_dump())
		for c in chunks.list_by_library(l.id):
			chunks_out.append(c.model_dump())
	return {"libraries": libraries, "documents": documents, "chunks": chunks_out}


@router.post("/trigger")
def trigger_reindex(index: IndexService = Depends(get_index_service)) -> Dict[str, Any]:
	# Follower can call this after applying snapshot to rebuild indexes using default types
	# For simplicity we do nothing here; actual rebuild is done in follower loop.
	return {"status": "ok"}
