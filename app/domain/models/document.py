"""
Document domain models.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.domain.models.common import MetadataBase, TimestampedModel


class DocumentMetadata(MetadataBase):
	pass


class Document(TimestampedModel):
	library_id: str = Field(..., min_length=1)
	title: str = Field(..., min_length=1, max_length=256)
	description: Optional[str] = Field(default=None, max_length=2048)
	metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)

	@field_validator("title")
	@classmethod
	def validate_title(cls, v: str) -> str:
		v = v.strip()
		if not v:
			raise ValueError("Document title cannot be empty")
		return v
