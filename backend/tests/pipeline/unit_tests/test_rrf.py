from app.pipeline.retrieval.fusion.rrf import RRFFusion
from app.pipeline.retrieval.models import RetrievedChunk


def chunk(chunk_id: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id="doc1",
        chunk_index=0,
        text=f"Chunk {chunk_id}",
        score=1.0,
    )


def test_single_ranking_preserves_order():
    fusion = RRFFusion()

    ranking = [
        chunk("A"),
        chunk("B"),
        chunk("C"),
    ]

    result = fusion.fuse(ranking)

    assert [c.chunk_id for c in result] == ["A", "B", "C"]


def test_duplicate_chunk_removed():
    fusion = RRFFusion()

    dense = [
        chunk("A"),
        chunk("B"),
    ]

    sparse = [
        chunk("A"),
        chunk("C"),
    ]

    result = fusion.fuse(dense, sparse)

    ids = [c.chunk_id for c in result]

    assert ids.count("A") == 1


def test_common_chunk_is_promoted():
    fusion = RRFFusion()

    dense = [
        chunk("A"),
        chunk("B"),
        chunk("C"),
    ]

    sparse = [
        chunk("C"),
        chunk("A"),
        chunk("D"),
    ]

    result = fusion.fuse(dense, sparse)

    ids = [c.chunk_id for c in result]

    assert ids.index("A") < ids.index("B")


def test_empty_rankings():
    fusion = RRFFusion()

    result = fusion.fuse([])

    assert result == []


def test_one_empty_ranking():
    fusion = RRFFusion()

    dense = [
        chunk("A"),
        chunk("B"),
    ]

    result = fusion.fuse([], dense)

    assert [c.chunk_id for c in result] == ["A", "B"]


def test_three_rankings():
    fusion = RRFFusion()

    dense = [
        chunk("A"),
        chunk("B"),
    ]

    sparse = [
        chunk("B"),
        chunk("C"),
    ]

    graph = [
        chunk("C"),
        chunk("A"),
    ]

    result = fusion.fuse(
        dense,
        sparse,
        graph,
    )

    ids = [c.chunk_id for c in result]

    assert set(ids) == {"A", "B", "C"}
    assert len(ids) == 3


def test_deterministic_output():
    fusion = RRFFusion()

    dense = [
        chunk("A"),
        chunk("B"),
        chunk("C"),
    ]

    sparse = [
        chunk("C"),
        chunk("A"),
        chunk("D"),
    ]

    first = fusion.fuse(dense, sparse)
    second = fusion.fuse(dense, sparse)

    assert [c.chunk_id for c in first] == [c.chunk_id for c in second]


def test_large_ranking():
    fusion = RRFFusion()

    dense = [chunk(str(i)) for i in range(1000)]

    result = fusion.fuse(dense)

    assert len(result) == 1000
    assert len({c.chunk_id for c in result}) == 1000


def test_rrf_k_parameter():
    fusion10 = RRFFusion(k=10)
    fusion60 = RRFFusion(k=60)

    dense = [
        chunk("A"),
        chunk("B"),
        chunk("C"),
    ]

    sparse = [
        chunk("C"),
        chunk("A"),
        chunk("D"),
    ]

    result10 = fusion10.fuse(dense, sparse)
    result60 = fusion60.fuse(dense, sparse)

    assert len(result10) == len(result60)
    assert {c.chunk_id for c in result10} == {c.chunk_id for c in result60}
