"""
Reader-Writer Lock (RWLock) implementation for thread-safe access.
Provides context managers for read and write locks.
"""
from __future__ import annotations

import threading
from contextlib import contextmanager


class RWLock:
	"""A reader-writer lock allowing concurrent reads and exclusive writes.
	
	This implementation prefers writers to avoid writer starvation.
	"""
	def __init__(self) -> None:
		self._readers = 0
		self._writers_waiting = 0
		self._writer_active = False
		self._cond = threading.Condition(threading.Lock())
	
	def acquire_read(self) -> None:
		with self._cond:
			while self._writer_active or self._writers_waiting > 0:
				self._cond.wait()
			self._readers += 1
	
	def release_read(self) -> None:
		with self._cond:
			self._readers -= 1
			if self._readers == 0:
				self._cond.notify_all()
	
	def acquire_write(self) -> None:
		with self._cond:
			self._writers_waiting += 1
			try:
				while self._writer_active or self._readers > 0:
					self._cond.wait()
				self._writer_active = True
			finally:
				self._writers_waiting -= 1
	
	def release_write(self) -> None:
		with self._cond:
			self._writer_active = False
			self._cond.notify_all()
	
	@contextmanager
	def read_lock(self):
		self.acquire_read()
		try:
			yield
		finally:
			self.release_read()
	
	@contextmanager
	def write_lock(self):
		self.acquire_write()
		try:
			yield
		finally:
			self.release_write()
