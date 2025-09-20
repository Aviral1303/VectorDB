"""
Documents router: CRUD within a library.
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, status, Response

from app.api.schemas import CreateDocumentRequest, DocumentResponse, UpdateDocumentRequest
from app.api.deps import get_document_service, require_leader
from app.domain.services.document_service import DocumentService


router = APIRouter(prefix="/api/v1/libraries/{library_id}/documents", tags=["Documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(library_id: str, payload: CreateDocumentRequest, _: None = Depends(require_leader), svc: DocumentService = Depends(get_document_service)) -> DocumentResponse:
	d = svc.create(library_id, title=payload.title, description=payload.description)
	return DocumentResponse(id=d.id, library_id=d.library_id, title=d.title, description=d.description)


@router.get("", response_model=List[DocumentResponse])
def list_documents(library_id: str, svc: DocumentService = Depends(get_document_service)) -> List[DocumentResponse]:
	docs = svc.list_by_library(library_id)
	return [DocumentResponse(id=d.id, library_id=d.library_id, title=d.title, description=d.description) for d in docs]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(library_id: str, document_id: str, svc: DocumentService = Depends(get_document_service)) -> DocumentResponse:
	d = svc.get(document_id)
	return DocumentResponse(id=d.id, library_id=d.library_id, title=d.title, description=d.description)


@router.patch("/{document_id}", response_model=DocumentResponse)
def update_document(library_id: str, document_id: str, payload: UpdateDocumentRequest, _: None = Depends(require_leader), svc: DocumentService = Depends(get_document_service)) -> DocumentResponse:
	d = svc.update(document_id, title=payload.title, description=payload.description)
	return DocumentResponse(id=d.id, library_id=d.library_id, title=d.title, description=d.description)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_document(library_id: str, document_id: str, _: None = Depends(require_leader), svc: DocumentService = Depends(get_document_service)) -> Response:
	svc.delete(document_id)
	return Response(status_code=status.HTTP_204_NO_CONTENT)
