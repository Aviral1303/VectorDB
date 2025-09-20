"""
Chunk domain models.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.domain.models.common import MetadataBase, TimestampedModel


class ChunkMetadata(MetadataBase):
	pass


class Chunk(TimestampedModel):
	library_id: str = Field(..., min_length=1)
	document_id: str = Field(..., min_length=1)
	text: str = Field(..., min_length=1)
	embedding: List[float] = Field(..., min_length=1)
	metadata: ChunkMetadata = Field(default_factory=ChunkMetadata)
	is_normalized: bool = Field(default=False, description="Whether embedding is L2-normalized")

	@field_validator("text")
	@classmethod
	def validate_text(cls, v: str) -> str:
		v = v.strip()
		if not v:
			raise ValueError("Chunk text cannot be empty")
		return v

	@field_validator("embedding")
	@classmethod
	def validate_embedding(cls, v: List[float]) -> List[float]:
		if not v:
			raise ValueError("Embedding cannot be empty")
		return v
