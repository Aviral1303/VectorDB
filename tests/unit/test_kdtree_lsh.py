from app.domain.indexes.kd_tree import KDTreeIndex
from app.domain.indexes.lsh import RandomHyperplaneLSHIndex


def test_kdtree_basic():
	idx = KDTreeIndex()
	vecs = [[1,0,0], [0,1,0], [0.7,0.7,0]]
	ids = ["a","b","c"]
	idx.build(vecs, ids)
	res = idx.search([1,0,0], k=2)
	# Expect 'a' first, then 'c' because it's closer than 'b'
	assert [r[0] for r in res] == ["a","c"]


def test_lsh_bucket_and_fallback():
	idx = RandomHyperplaneLSHIndex(num_planes=8, seed=123)
	vecs = [[1,0,0], [0,1,0], [0.9,0.1,0]]
	ids = ["a","b","c"]
	idx.build(vecs, ids)
	res = idx.search([1,0,0], k=2)
	# Should contain 'a' or 'c' first depending on hashing; ensure 'a' is in top-2 and score >= 0.5
	ids_returned = [r[0] for r in res]
	assert "a" in ids_returned
	assert res[0][1] >= 0.5
