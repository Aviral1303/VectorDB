"""
Common domain models and utilities.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def generate_id() -> str:
	"""Generate a new UUIDv4 string."""
	return str(uuid4())


class TimestampedModel(BaseModel):
	"""Base model with id and timestamps."""
	id: str = Field(default_factory=generate_id)
	created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
	updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())

	def touch(self) -> None:
		self.updated_at = datetime.utcnow()


class MetadataBase(BaseModel):
	"""Base metadata with common optional fields."""
	source: Optional[str] = None
	tags: List[str] = Field(default_factory=list)
	author: Optional[str] = None
	created_by: Optional[str] = None

	@field_validator("tags")
	@classmethod
	def validate_tags(cls, v: List[str]) -> List[str]:
		# Ensure unique, non-empty tags trimmed to reasonable length
		unique = []
		seen = set()
		for tag in v:
			clean = tag.strip()
			if not clean:
				continue
			if len(clean) > 64:
				raise ValueError("Tag too long (max 64 chars)")
			if clean not in seen:
				seen.add(clean)
				unique.append(clean)
		return unique
