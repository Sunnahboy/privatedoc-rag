from app.pipeline.indexing.tantivy_indexer import TantivyIndexer


async def main():
    index = TantivyIndexer()

    searcher = index.searcher

    print(f"Total documents: {searcher.num_docs}")

    for _, doc_address in searcher.search(
        index.index.parse_query("*", ["text"]),
        limit=20,
    ).hits:
        doc = searcher.doc(doc_address)
        print("-" * 80)
        print("Document ID :", doc["document_id"][0])
        print("Chunk ID    :", doc["chunk_id"][0])
        print("Chunk Index :", doc["chunk_index"][0])
        print("Text        :", doc["text"][0][:200])


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
