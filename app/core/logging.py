"""
Logging configuration for the Vector DB application.
Supports both structured JSON logging and human-readable text format.
"""
import logging
import sys
from typing import Dict, Any
import json
from datetime import datetime

from app.core.settings import settings


def _unquote(value: str) -> str:
	if isinstance(value, str) and len(value) >= 2:
		if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
			return value[1:-1]
	return value


class JSONFormatter(logging.Formatter):
	"""Custom JSON formatter for structured logging."""
	
	def format(self, record: logging.LogRecord) -> str:
		"""Format log record as JSON."""
		log_entry: Dict[str, Any] = {
			"timestamp": datetime.utcnow().isoformat() + "Z",
			"level": record.levelname,
			"logger": record.name,
			"message": record.getMessage(),
		}
		
		# Add extra fields from record
		if hasattr(record, "request_id"):
			log_entry["request_id"] = record.request_id
		if hasattr(record, "library_id"):
			log_entry["library_id"] = record.library_id
		if hasattr(record, "user_id"):
			log_entry["user_id"] = record.user_id
		if hasattr(record, "duration_ms"):
			log_entry["duration_ms"] = record.duration_ms
		
		# Add exception info if present
		if record.exc_info:
			log_entry["exception"] = self.formatException(record.exc_info)
		
		return json.dumps(log_entry, ensure_ascii=False)


def setup_logging() -> None:
	"""Configure application logging based on settings."""
	
	# Remove existing handlers
	root_logger = logging.getLogger()
	for handler in root_logger.handlers[:]:
		root_logger.removeHandler(handler)
	
	# Sanitize level and format in case env vars include quotes
	level_name = str(settings.log_level).strip()
	level_name = _unquote(level_name).upper()
	if not hasattr(logging, level_name):
		level_name = "INFO"
	
	fmt_kind = str(settings.log_format).strip()
	fmt_kind = _unquote(fmt_kind).lower()
	
	# Create console handler
	console_handler = logging.StreamHandler(sys.stdout)
	
	# Set formatter based on configuration
	if fmt_kind == "json":
		formatter = JSONFormatter()
	else:
		formatter = logging.Formatter(
			fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
			datefmt="%Y-%m-%d %H:%M:%S"
		)
	
	console_handler.setFormatter(formatter)
	
	# Configure root logger
	root_logger.addHandler(console_handler)
	root_logger.setLevel(getattr(logging, level_name))
	
	# Set specific loggers to appropriate levels
	logging.getLogger("uvicorn").setLevel(logging.INFO)
	logging.getLogger("uvicorn.access").setLevel(logging.INFO)
	logging.getLogger("fastapi").setLevel(logging.INFO)
	
	# Reduce noise from HTTP libraries
	logging.getLogger("httpx").setLevel(logging.WARNING)
	logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
	"""Get a logger instance with the given name."""
	return logging.getLogger(name)


# Context manager for adding request context to logs
class LogContext:
	"""Context manager for adding context to log records."""
	
	def __init__(self, **context):
		self.context = context
		self.old_factory = logging.getLogRecordFactory()
	
	def __enter__(self):
		def record_factory(*args, **kwargs):
			record = self.old_factory(*args, **kwargs)
			for key, value in self.context.items():
				setattr(record, key, value)
			return record
		
		logging.setLogRecordFactory(record_factory)
		return self
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		logging.setLogRecordFactory(self.old_factory)
