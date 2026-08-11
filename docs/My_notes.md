## System Architecture Note: Image & Diagram Extraction Status
    Through  recent refactoring of the privatedoc-rag backend,  successfully transitioned the OCR implementation into an independent, reusable service following the Strategy Pattern, SOLID principles, and Dependency Injection. By decoupling OCR from PDFExtractor, we created a modular BaseOCR interface (RapidOCREngine) that can be easily injected into future document extractors like DOCX or PPTX without duplicating code. To eliminate heavy runtime latency, we implemented a FastAPI lifespan startup hook to pre-load and warm up the ONNX CUDA models into VRAM, while simultaneously optimizing Ollama's embedding pipeline with safer batch sizes and bounded semaphores to prevent local GPU token-limit crashes.

    Regarding document images and design diagrams, the system currently performs text extraction using RapidOCR—meaning any text labels, titles, or code snippets embedded inside diagrams are successfully read, chunked, and indexed into Qdrant for RAG retrieval. However, because a Vision-Language Model (like LLaVA) has not been integrated yet, the system captures the text inside diagrams rather than performing full visual reasoning, meaning it can answer questions based on text labels but cannot inherently interpret spatial layouts, shapes, or connecting arrows.

## Tomorrow
     I'll focus on improving the ingestion pipeline by preventing duplicate document uploads through content hashing and metadata validation, ensuring the same document cannot be indexed multiple times. I'll also implement a reranking stage after hybrid retrieval to reorder retrieved chunks by semantic relevance before generation, improving answer quality and citation accuracy.

## rejecting duplicates design

                 Upload
                    │
                    ▼
              SHA-256 hash
                    │
             ┌──────┴──────┐
             │             │
          EXISTS?        NEW?
             │             │
          reject          UUID
                           │
                           ▼
                       ingest


## current design
                    Next.js
                       │
                       ▼
                    FastAPI
                       │
              ┌────────┴────────┐
              │                 │
           RAG Ask          Upload API
              │                 │
              ▼                 ▼
        Hybrid Retrieval     RabbitMQ
              │                 │
       RRF → FlashRank          ▼
              │              Worker
              ▼                 │
           Ollama               ▼
                            IngestionPipeline
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
                Extraction    Embedding    Indexing
                    │            │         ↙      ↘
                   OCR         Ollama    Qdrant   Tantivy
  ## 
  app/
├── api/
│   ├── document.py
│   ├── rag_router.py
│   └── health.py
│
├── services/
│   └── document_service.py
│
├── messaging/
│   ├── __init__.py
│   ├── connection.py          # RabbitMQ connection/channel management
│   ├── exchanges.py           # Exchange declarations
│   ├── queues.py              # Queue declarations + bindings
│   ├── publisher.py           # Publish jobs
│   └── messages.py            # Message schemas/types
│
├── workers/
│   ├── __init__.py
│   ├── ingestion_worker.py    # Consumes document.ingest
│   ├── ocr_worker.py          # OCR needs isolation/visual model for images
│   └── evaluation_worker.py   # Later
│
├── pipeline/
│   ├── extraction/
│   ├── ocr/
│   ├── cleaning/
│   ├── chunking/
│   ├── embeddings/
│   ├── indexing/
│   ├── retrieval/
│   ├── generation/
│   └── ingestion/
│
├── orchestration/
│   └── rag_pipeline.py
│
├── models/
├── schemas/
├── utils/
└── config.py


## for connection
                   [ Application Startup ]
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │     initialize()      │
                     └───────────┬───────────┘
                                 │
                   ┌─────────────┴─────────────┐
                   ▼                           ▼
       ┌───────────────────────┐   ┌───────────────────────┐
       │  _create_connection() │   │   _create_channel()   │
       │ (1 Robust Connection) │   │ (Checks readiness via │
       └───────────┬───────────┘   │    channel.ready())   │
                   │               └───────────┬───────────┘
                   │                           │
                   └─────────────┬─────────────┘
                                 ▼
                     ┌───────────────────────┐
                     │   Pool Initialized    │
                     └───────────┬───────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌──────────────────┐   ┌───────────────────┐   ┌──────────────────┐
│  is_healthy()    │   │get_channel_pool() │   │create_consumer_  │
│                  │   │                   │   │channel()         │
│ • Checks if con- │   │ • Borrows short-  │   │                  │
│   nection/pool   │   │   lived channel   │   │ • Spawns brand   │
│   are active.    │   │   for publishing. │   │   new, unpooled  │
│ • Returns False  │   │ • Auto-returns to │   │   channel for    │
│   if pool full.  │   │   pool when done. │   │   long consumers.│
└──────────────────┘   └───────────────────┘   └──────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │        close()        │
                     │  (Graceful Shutdown)  │
                     └───────────────────────┘
                     