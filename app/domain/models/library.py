"""
Library domain models.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.core.settings import IndexType
from app.domain.models.common import MetadataBase, TimestampedModel


class LibraryMetadata(MetadataBase):
	owner: Optional[str] = None


class Library(TimestampedModel):
	name: str = Field(..., min_length=1, max_length=128)
	description: Optional[str] = Field(default=None, max_length=1024)
	embedding_dimension: int = Field(..., gt=0, le=4096)
	default_index_type: IndexType = Field(default=IndexType.BRUTE_FORCE)
	metadata: LibraryMetadata = Field(default_factory=LibraryMetadata)
	data_version: int = Field(default=0, ge=0)

	@field_validator("name")
	@classmethod
	def validate_name(cls, v: str) -> str:
		v = v.strip()
		if not v:
			raise ValueError("Library name cannot be empty")
		return v
