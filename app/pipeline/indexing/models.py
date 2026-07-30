from dataclasses import dataclass


@dataclass(slots=True)
class IndexingResult:
    indexed_count: int
    collection_name: str
