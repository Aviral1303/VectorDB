"""
Filter DTOs for metadata-based filtering in queries.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ChunkFilter(BaseModel):
	tags_any: Optional[List[str]] = Field(default=None)
	tags_all: Optional[List[str]] = Field(default=None)
	author_in: Optional[List[str]] = Field(default=None)
	created_at_from: Optional[datetime] = Field(default=None)
	created_at_to: Optional[datetime] = Field(default=None)
	text_contains: Optional[str] = Field(default=None)
