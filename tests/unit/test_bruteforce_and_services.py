from app.core.settings import IndexType, settings
from app.domain.indexes.brute_force import BruteForceIndex
from app.domain.concurrency.registry import LockRegistry
from app.domain.concurrency.versioning import VersionManager
from app.domain.repositories.chunks import ChunkRepository
from app.domain.services.index_service import IndexService
from app.domain.services.query_service import QueryService
from app.domain.models.chunk import Chunk


def test_bruteforce_search_basic():
	idx = BruteForceIndex(pre_normalize=True)
	vecs = [[1,0,0], [0,1,0], [0.9,0.1,0]]
	ids = ["a","b","c"]
	idx.build(vecs, ids)
	res = idx.search([1,0,0], k=2)
	assert [r[0] for r in res] == ["a","c"]


def test_index_service_build_and_search():
	locks = LockRegistry()
	versions = VersionManager()
	svc = IndexService(locks, versions)
	chunks_repo = ChunkRepository()
	lib = "lib1"
	cs = [
		Chunk(library_id=lib, document_id="d1", text="t1", embedding=[1,0,0]),
		Chunk(library_id=lib, document_id="d1", text="t2", embedding=[0,1,0]),
	]
	svc.build_index(lib, IndexType.BRUTE_FORCE, cs)
	res = svc.search(lib, [1,0,0], k=1)
	assert res and res[0][0] == cs[0].id


def test_query_service_with_stale_policy():
	locks = LockRegistry()
	versions = VersionManager()
	chunks_repo = ChunkRepository()
	index_svc = IndexService(locks, versions)
	q = QueryService(locks, versions, chunks_repo, index_svc)
	lib = "lib1"
	c1 = Chunk(library_id=lib, document_id="d1", text="t1", embedding=[1,0,0])
	c2 = Chunk(library_id=lib, document_id="d1", text="t2", embedding=[0,1,0])
	chunks_repo.create(c1)
	chunks_repo.create(c2)
	index_svc.build_index(lib, IndexType.BRUTE_FORCE, [c1, c2])
	# Mutate data to make index stale
	versions.bump_data(lib)
	# allow_stale_index True by default -> will use existing index
	res1 = q.knn(lib, [1,0,0], k=1)
	assert res1 and res1[0][0] == c1.id
	# Now force fallback by disabling stale allowance
	settings.allow_stale_index = False
	try:
		res2 = q.knn(lib, [0,1,0], k=1)
		assert res2 and res2[0][0] == c2.id
	finally:
		settings.allow_stale_index = True
