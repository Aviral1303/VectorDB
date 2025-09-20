"""
Application settings configuration using Pydantic BaseSettings.
Loads configuration from environment variables with sensible defaults.
"""
from enum import Enum
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Environment(str, Enum):
	"""Application environment types."""
	DEVELOPMENT = "development"
	PRODUCTION = "production"
	TESTING = "testing"


class IndexType(str, Enum):
	"""Available index types for vector search."""
	BRUTE_FORCE = "brute_force"
	KD_TREE = "kd_tree"
	LSH = "lsh"


class NodeRole(str, Enum):
	LEADER = "leader"
	FOLLOWER = "follower"


def _strip_quotes(value: object) -> object:
	if isinstance(value, str) and len(value) >= 2:
		if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
			return value[1:-1]
	return value


class Settings(BaseSettings):
	"""Application settings loaded from environment variables."""
	
	# Application
	app_name: str = Field(default="Vector DB API", description="Application name")
	app_version: str = Field(default="1.0.0", description="Application version")
	environment: Environment = Field(default=Environment.DEVELOPMENT, description="Application environment")
	debug: bool = Field(default=True, description="Enable debug mode")
	
	# Server
	host: str = Field(default="0.0.0.0", description="Server host")
	port: int = Field(default=8000, description="Server port")
	
	# Logging
	log_level: str = Field(default="INFO", description="Logging level")
	log_format: str = Field(default="json", description="Log format: json or text")
	
	# Vector DB
	default_index_type: IndexType = Field(default=IndexType.BRUTE_FORCE, description="Default index type for new libraries")
	allow_stale_index: bool = Field(default=True, description="Allow serving results from stale indexes")
	max_embedding_dimension: int = Field(default=4096, description="Maximum allowed embedding dimension")
	
	# Embedding Service
	embedding_provider: str = Field(default="cohere", description="Embedding provider: cohere or none")
	cohere_api_key: Optional[str] = Field(default=None, description="Cohere API key for embedding generation")
	cohere_model: str = Field(default="embed-english-v3.0", description="Cohere embedding model")
	embedding_cache_size: int = Field(default=1000, description="In-memory embedding cache size")
	
	# Persistence (optional)
	persistence_enabled: bool = Field(default=False, description="Enable persistence to disk")
	persistence_dir: str = Field(default="./data", description="Directory for persistent storage")
	
	# Concurrency
	max_concurrent_index_builds: int = Field(default=2, description="Maximum concurrent index builds")
	index_build_timeout_seconds: int = Field(default=300, description="Timeout for index builds in seconds")
	
	# Cluster role
	node_role: NodeRole = Field(default=NodeRole.LEADER, description="Node role: leader or follower")
	leader_url: Optional[str] = Field(default=None, description="Leader base URL for follower replication")
	replication_interval_seconds: int = Field(default=10, description="Follower replication poll interval in seconds")

	# Validators to tolerate quoted env values
	@field_validator("environment", mode="before")
	@classmethod
	def _unquote_environment(cls, v: object) -> object:
		return _strip_quotes(v)

	@field_validator("default_index_type", mode="before")
	@classmethod
	def _unquote_default_index_type(cls, v: object) -> object:
		return _strip_quotes(v)

	@field_validator("node_role", mode="before")
	@classmethod
	def _unquote_node_role(cls, v: object) -> object:
		return _strip_quotes(v)

	@field_validator("log_level", "log_format", "host", "app_name", "app_version", "embedding_provider", "cohere_api_key", "cohere_model", "persistence_dir", "leader_url", mode="before")
	@classmethod
	def _unquote_generic(cls, v: object) -> object:
		return _strip_quotes(v)
	
	class Config:
		"""Pydantic configuration."""
		env_file = ".env"
		env_file_encoding = "utf-8"
		case_sensitive = False
		# Allow loading from environment variables with APP_ prefix
		env_prefix = "VECTORDB_"


# Global settings instance
settings = Settings()
