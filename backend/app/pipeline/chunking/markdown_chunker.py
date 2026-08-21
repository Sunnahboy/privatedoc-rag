# app/pipeline/chunking/markdown_chunker.py
import asyncio
from typing import List
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from app.pipeline.chunking.base import BaseChunker
from app.pipeline.chunking.models import Chunk
from app.pipeline.cleaning.models import CleaningResult
from app.utils.id_id_utils import generate_chunk_id

class MarkdownSemanticChunker(BaseChunker):
    def __init__(self, chunk_size: int = 2000, chunk_overlap: int = 200):
        # 1. Semantic Splitter (Splits at headers)
        self.headers_to_split_on = [
            ("#", "Header_1"),
            ("##", "Header_2"),
            ("###", "Header_3"),
            ("####", "Header_4"),
        ]
        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on,
            strip_headers=False
        )
        
        # 2. Fallback Length Splitter (For massive sections)
        self.length_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    async def chunk(
        self,
        cleaning_result: CleaningResult,
        document_id: str = "unknown_doc",
    ) -> list[Chunk]:
        if hasattr(cleaning_result, 'text') and cleaning_result.text:
            content = cleaning_result.text
        elif hasattr(cleaning_result, 'cleaned_text') and cleaning_result.cleaned_text:
            content = cleaning_result.cleaned_text
        elif hasattr(cleaning_result, 'pages') and cleaning_result.pages:
            content = "\n\n".join(cleaning_result.pages)
        else:
            content = str(cleaning_result)

        if not content or not content.strip():
            return []

        # Prefer a document_id already attached to the result; fall back to the argument.
        doc_id = getattr(cleaning_result, "document_id", document_id)

        return await asyncio.to_thread(
            self._sync_chunk,
            content,
            doc_id,
        )

    def _sync_chunk(self, text: str, document_id: str) -> list[Chunk]:
        header_chunks = self.header_splitter.split_text(text)
        final_langchain_chunks = self.length_splitter.split_documents(header_chunks)
        
        chunks = []
        current_search_index = 0
        
        for index, lc_chunk in enumerate(final_langchain_chunks):
            chunk_text = lc_chunk.page_content.strip()
            
            # Find exact character positions for highlighting/citations
            start_char = text.find(chunk_text[:50], current_search_index)
            if start_char == -1:
                start_char = current_search_index
            end_char = start_char + len(chunk_text)
            
            # Advance search index
            current_search_index = start_char + max(1, len(chunk_text) // 2)

            # Generate the Chunk using the correctly scoped document_id
            chunks.append(
                Chunk(
                    chunk_id=generate_chunk_id(document_id, index),
                    document_id=document_id,
                    chunk_index=index,
                    text=chunk_text,
                    start_char=start_char,
                    end_char=end_char,
                    page_number=None, 
                    metadata=lc_chunk.metadata
                )
            )
            
        return chunks