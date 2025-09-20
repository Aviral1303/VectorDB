"""
Minimal Python SDK client for the Vector DB API.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx


class VectorDBClient:
	def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 10.0) -> None:
		self._base = base_url.rstrip("/")
		self._timeout = timeout
		self._client = httpx.Client(timeout=self._timeout)
	
	def close(self) -> None:
		self._client.close()
	
	# Libraries
	def create_library(self, name: str, embedding_dimension: int, default_index_type: str = "brute_force", description: Optional[str] = None) -> Dict[str, Any]:
		payload = {
			"name": name,
			"embedding_dimension": embedding_dimension,
			"default_index_type": default_index_type,
			"description": description,
		}
		r = self._client.post(f"{self._base}/api/v1/libraries", json=payload)
		r.raise_for_status()
		return r.json()
	
	def list_libraries(self) -> List[Dict[str, Any]]:
		r = self._client.get(f"{self._base}/api/v1/libraries")
		r.raise_for_status()
		return r.json()
	
	def delete_library(self, library_id: str) -> None:
		r = self._client.delete(f"{self._base}/api/v1/libraries/{library_id}")
		r.raise_for_status()
	
	# Documents
	def create_document(self, library_id: str, title: str, description: Optional[str] = None) -> Dict[str, Any]:
		payload = {"title": title, "description": description}
		r = self._client.post(f"{self._base}/api/v1/libraries/{library_id}/documents", json=payload)
		r.raise_for_status()
		return r.json()
	
	def list_documents(self, library_id: str) -> List[Dict[str, Any]]:
		r = self._client.get(f"{self._base}/api/v1/libraries/{library_id}/documents")
		r.raise_for_status()
		return r.json()
	
	# Chunks
	def create_chunk(self, library_id: str, document_id: str, text: str, embedding: Optional[List[float]] = None, use_embedding_service: bool = False) -> Dict[str, Any]:
		payload: Dict[str, Any] = {"text": text, "use_embedding_service": use_embedding_service}
		if embedding is not None:
			payload["embedding"] = embedding
		r = self._client.post(f"{self._base}/api/v1/libraries/{library_id}/documents/{document_id}/chunks", json=payload)
		r.raise_for_status()
		return r.json()
	
	def list_chunks(self, library_id: str) -> List[Dict[str, Any]]:
		r = self._client.get(f"{self._base}/api/v1/libraries/{library_id}/chunks")
		r.raise_for_status()
		return r.json()
	
	# Index
	def build_index(self, library_id: str, index_type: str = "brute_force") -> Dict[str, Any]:
		r = self._client.post(f"{self._base}/api/v1/libraries/{library_id}/index:build", json={"index_type": index_type})
		r.raise_for_status()
		return r.json()
	
	def index_status(self, library_id: str) -> Dict[str, Any]:
		r = self._client.get(f"{self._base}/api/v1/libraries/{library_id}/index:status")
		r.raise_for_status()
		return r.json()
	
	# Query
	def query(self, library_id: str, k: int = 5, query_embedding: Optional[List[float]] = None, query_text: Optional[str] = None, use_embedding_service: bool = False, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
		payload: Dict[str, Any] = {"k": k, "use_embedding_service": use_embedding_service}
		if query_embedding is not None:
			payload["query_embedding"] = query_embedding
		if query_text is not None:
			payload["query_text"] = query_text
		if filter is not None:
			payload["filter"] = filter
		r = self._client.post(f"{self._base}/api/v1/libraries/{library_id}/query", json=payload)
		r.raise_for_status()
		return r.json()
