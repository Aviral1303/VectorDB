"""
EmbeddingService: generate embeddings from text using Cohere or a local deterministic fallback.
"""
from __future__ import annotations

from typing import List
import hashlib
import math

import httpx

from app.core.settings import settings
from app.domain.indexes.base import normalize


class EmbeddingService:
	"""Embeddings via Cohere (if configured) or local fallback hash embedding.
	
	Local fallback uses a simple token hashing to accumulate into a fixed-size vector.
	This is deterministic and good for local smoke tests without external API keys.
	"""
	def __init__(self) -> None:
		self._provider = settings.embedding_provider.lower()
		self._cohere_api_key = settings.cohere_api_key
		self._cohere_model = settings.cohere_model
	
	def embed_text(self, text: str, target_dimension: int) -> List[float]:
		if self._provider == "cohere" and self._cohere_api_key:
			try:
				vec = self._embed_with_cohere(text)
				return self._fit_dimension(vec, target_dimension)
			except Exception:
				# Fall back to local embedding on any error
				pass
		# Fallback
		return self._fit_dimension(self._local_hash_embedding(text, target_dimension), target_dimension)
	
	def _embed_with_cohere(self, text: str) -> List[float]:
		url = "https://api.cohere.ai/v1/embed"
		headers = {
			"Authorization": f"Bearer {self._cohere_api_key}",
			"Content-Type": "application/json",
		}
		payload = {
			"model": self._cohere_model,
			"input": [text],
		}
		with httpx.Client(timeout=15.0) as client:
			resp = client.post(url, headers=headers, json=payload)
			resp.raise_for_status()
			data = resp.json()
			# Cohere returns embeddings under key 'embeddings' or 'data' depending on API version
			if "embeddings" in data:
				embeds = data["embeddings"][0]
			elif "data" in data and data["data"] and "embedding" in data["data"][0]:
				embeds = data["data"][0]["embedding"]
			else:
				raise RuntimeError("Unexpected Cohere embed response shape")
			return list(map(float, embeds))
	
	def _fit_dimension(self, vec: List[float], target_dimension: int) -> List[float]:
		if len(vec) == target_dimension:
			return vec
		if len(vec) > target_dimension:
			return vec[:target_dimension]
		# pad with zeros
		return vec + [0.0] * (target_dimension - len(vec))
	
	def _local_hash_embedding(self, text: str, dim: int) -> List[float]:
		if dim <= 0:
			return []
		acc = [0.0] * dim
		for token in text.lower().split():
			h = hashlib.md5(token.encode("utf-8")).digest()
			# Use 4 bytes at a time to create indices and signs
			for i in range(0, min(len(h), 4 * max(1, dim // 8)), 4):
				idx = int.from_bytes(h[i:i+2], "big") % dim
				sgn = 1.0 if (h[i+2] % 2 == 0) else -1.0
				acc[idx] += sgn
		# Normalize for cosine friendliness
		return normalize(acc)
