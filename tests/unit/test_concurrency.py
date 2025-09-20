import threading
import time

from app.domain.concurrency.rwlock import RWLock
from app.domain.concurrency.versioning import VersionManager


def test_rwlock_allows_concurrent_reads():
	lock = RWLock()
	counter = 0
	
	def reader():
		nonlocal counter
		with lock.read_lock():
			time.sleep(0.01)
			counter += 1
	
	threads = [threading.Thread(target=reader) for _ in range(10)]
	for t in threads:
		t.start()
	for t in threads:
		t.join()
	
	assert counter == 10


def test_rwlock_exclusive_write():
	lock = RWLock()
	state = []
	
	def writer(val):
		with lock.write_lock():
			current = list(state)
			time.sleep(0.005)
			current.append(val)
			state.clear()
			state.extend(current)
	
	threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
	for t in threads:
		t.start()
	for t in threads:
		t.join()
	
	assert sorted(state) == [0,1,2,3,4]


def test_version_manager():
	vm = VersionManager()
	lib = "lib-1"
	vi = vm.get(lib)
	assert vi.data_version == 0 and vi.index_version == -1
	vm.bump_data(lib)
	assert vm.get(lib).data_version == 1
	assert vm.is_index_stale(lib) is True
	vm.set_index_version(lib, 1)
	assert vm.is_index_stale(lib) is False
