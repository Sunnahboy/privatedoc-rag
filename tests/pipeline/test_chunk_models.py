from app.pipeline.chunking.models import Chunk


def test_chunk_creation():
    chuck = Chunk(
        chunk_id="1",
        document_id="doc1",
        chunk_index=0,
        text="Hello",
        start_char=0,
        end_char=5,
    )

    assert chuck.text == "Hello"
    assert chuck.start_char == 0
    assert chuck.end_char == 5
