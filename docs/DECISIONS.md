# Decision Records

## Decision 001: Use FastAPI for Backend

Date: 2026-06-30
Context:
I need a backend framework to orchestrate my self-hosted RAG pipeline. It must efficiently handle asynchronous requests to local LLM services and vector databases, validate incoming document uploads securely, and serve a clean API interface for our frontend application.

Decision:
Use FastAPI as the backend framework.

Reason:
FastAPI provides clean API routing, request validation, automatic OpenAPI documentation, async support, and strong compatibility with Python-based AI systems.

Alternatives considered:
- Flask
- Django
- Express.js

Tradeoff:
FastAPI is less full-stack than Django, but it is lighter and better suited for API-first AI services.

Status:
Accepted.


## Embedding Pipeline Architecture

Implemented the foundational architecture for the embedding stage of the RAG pipeline. Added a provider-agnostic embedding interface, embedding data models, custom exception hierarchy, provider factory, Ollama embedder skeleton, configuration settings, and unit tests. This establishes a modular design that allows different embedding providers to be added while keeping the rest of the pipeline unchanged.

Implemented the embedding generation stage for the RAG pipeline. Added a local Ollama embedder capable of converting document chunks into dense vector representations through a provider-independent interface. The implementation includes configuration support, structured embedding results, and custom exception handling, preparing the pipeline for vector indexing in Qdrant.

## for embeddings
Once that's working, we'll profile the bottlenecks with real measurements and then introduce batching, concurrency, and background processing.


## further reading
Reading Order (2–4 hours)
    .What is a vector database? (20 min)
    .Qdrant concepts (collections, points, payloads) (30 min)
    .Cosine similarity vs Euclidean vs Dot Product (30–45 min)
    .Approximate Nearest Neighbor (ANN) and HNSW (high level) (30–45 min)
    .Qdrant Python client basics (30 min)
    .Batch upserts and payload filtering (30 min)
    .Questions you should be able to answer afterwards

.What problem does a vector database solve that PostgreSQL doesn't?
.Why is cosine similarity commonly used for text embeddings?
.What is the difference between a vector and a payload?
.Why must all vectors in a collection have the same dimension?
.Why use upsert() instead of separate insert/update operations?
.Why are batch upserts more efficient than one point at a time?
.What happens if you try to insert a 384-dimensional vector into a 768-dimensional collection?
.Why does Qdrant use HNSW instead of comparing every vector?
.How does metadata filtering improve retrieval?
.Why should the indexer operate on EmbeddingResult instead of Chunk?
 ## Features we'll implement
    Qdrant client wrapper
        Reusable async client
        Connection management
    Collection management
        Create collection if missing
        Validate vector size
        Configure distance metric
    Batch upserts
        Similar to the embedder
        Send points in configurable batches
    Payload mapping
        Store text and metadata alongside vectors
    Error handling
        Wrap Qdrant exceptions
        Clear domain-specific errors
    Benchmark script
        Measure indexing throughput
        Compare different batch sizes


## Decision XXX: Introduce a Retrieval Layer

Context:
The application should not depend directly on Qdrant models.

Decision:
Map Qdrant ScoredPoint objects into RetrievedChunk domain models.

Reason:
Keeps the application independent of the underlying vector database and makes replacing Qdrant possible without changing business logic.

Tradeoff:
Adds a small mapping step but greatly reduces coupling.

Status:
Accepted.


API orchestration (RAGPipeline + FastAPI endpoints)
Frontend integration
End-to-end testing
Hybrid Search
Reranking
Caching
Background workers
Evaluation
Monitoring

## offline first archetecture


###
Yes, this is the architecture I would choose with one refinement.

Your guiding principle should be **open for extension, closed for modification**. We already have a working `QdrantRetriever`. We shouldn't keep modifying it every time we add a new retrieval strategy. Instead, every retrieval strategy becomes an independent component and a single orchestrator combines them. This is how most production search systems are designed.

The architecture should be:

```text
Question
    │
    ▼
HybridRetriever
   /         \
Dense      Sparse
(Qdrant)    (BM25)
   \         /
    \       /
     RRF Fusion
         │
         ▼
 RetrievalResult
         │
         ▼
 PromptBuilder
         │
         ▼
       LLM
```

The responsibilities are clean. `QdrantRetriever` performs semantic search only. `BM25Retriever` performs lexical (keyword) search only. `RRFFusion` knows only how to merge ranked lists. `HybridRetriever` orchestrates both retrievers concurrently using `asyncio.gather()` and returns a single `RetrievalResult`. None of these classes know about prompting or generation.

I would make one directory change. Don't organize by algorithm ("dense", "sparse"). Organize by responsibility.

```text
└app/
└── pipeline/
    └── retrieval/
        ├── interface.py
        ├── models.py
        ├── exceptions.py
        │
        ├── qdrant_retriever.py
        ├── bm25_retriever.py
        ├── hybrid_retriever.py
        │
        ├── fusion/
        │    ├── base.py
        │    └── rrf.py
        │
        └── bm25/
             ├── tantivy_index.py
             └── base.py
```

This scales better. If later you add Elasticsearch, OpenSearch, ColBERT, SPLADE, GraphRAG, or Knowledge Graph retrieval, you simply add another retriever instead of reorganizing the project.

For fusion, there are several approaches. Weighted score fusion adds weighted dense and sparse scores together, but it requires careful score normalization because each retriever produces scores on completely different scales. Max-score fusion simply keeps the highest score from either retriever, but it throws away useful ranking information. Learning-to-rank methods such as LambdaMART generally produce the best results, but they require labeled training data and introduce significant operational complexity. Reciprocal Rank Fusion (RRF) is the best choice here because it combines **ranks instead of scores**, requires no normalization, is simple to implement, robust across different retrievers, and is widely adopted in production systems including Azure AI Search, Elasticsearch, OpenSearch, Weaviate, Pinecone, and Qdrant.

Our implementation plan should be incremental. First, implement the BM25 index and `BM25Retriever` and verify it independently. Second, implement `RRFFusion` with unit tests. Third, build `HybridRetriever`, which executes both retrieval strategies concurrently and fuses their ranked results. Finally, change the RAG pipeline to depend on the retrieval interface and instantiate `HybridRetriever` instead of `QdrantRetriever`. No changes should be required to the embedding, indexing, generation, prompt building, or API layers. This keeps the modification localized to the retrieval subsystem and follows production-quality software design.


###
Your architecture changes completely.

What you have now (development)
User
   │
FastAPI
   │
Ollama (1 instance)
   │
llama3.1:8b

This is for development and local deployment.

What a production RAG service looks like
                Load Balancer
                      │
      ┌───────────────┼────────────────┐
      │               │                │
 API Server 1   API Server 2    API Server 3
      │               │                │
      └───────────────┼────────────────┘
                      │
             Redis / Cache Layer
                      │
        ┌─────────────┼─────────────┐
        │                           │
   Qdrant Cluster             Tantivy Nodes
        │                           │
        └─────────────┬─────────────┘
                      │
              Inference Gateway
        ┌─────────────┼─────────────┐
        │             │             │
   LLM Server 1  LLM Server 2  LLM Server N

Notice something:

Inference is its own service.

Millions of users don't all hit one model

Imagine 1 million users.

They don't queue behind one GPU.

Instead you have:

GPU #1
GPU #2
GPU #3
...
GPU #500

A load balancer routes requests.

Exactly like web servers.

Why ChatGPT feels instant

OpenAI isn't running:

1 GPU

They're running:

Thousands of GPUs

with

batching
scheduling
KV cache reuse
optimized inference engines
model parallelism
speculative decoding
continuous batching
Your RAG system

Your retrieval already scales well.

Qdrant
≈ 20 ms

Tantivy
≈ 1 ms

RRF
≈ 0.03 ms

Those numbers are excellent.

The expensive part is:

Generate answer

Every LLM application pays this cost.

How companies solve it

They don't make the model faster.

They reduce how often they call it.

Example:

User asks question
        │
Cache?
   │
Yes ─────► Return instantly
   │
No
   │
Retrieve
   │
Generate
   │
Store in cache

The second identical question might take

20 ms

instead of

6 seconds.
They also use smaller models

Not every request needs an 8B model.

Example routing:

Greeting
        │
        ▼
  Tiny 1B model

Simple lookup
        │
        ▼
   3B model

Complex reasoning
        │
        ▼
   8B / 70B model

Most production systems don't send every query to their largest model.

For your project

Your goal is not to support millions of users on your laptop.

Your goal is to design an architecture that can scale.

Your current roadmap is already heading there:

✅ Document Upload
✅ Extraction
✅ Cleaning
✅ Chunking
✅ Embeddings
✅ Qdrant
✅ Tantivy (BM25)
✅ Hybrid Retrieval
✅ RRF
✅ Generation
✅ Profiling

✅ Delete pipeline
✅ API testing
✅ Reranker
⬜ Frontend (Next.js)
⬜ End-to-end testing
⬜ Evaluation framework
⬜ Background workers
⬜ Redis caching
⬜ Monitoring (Prometheus/Grafana)

----------------------------
Version 2
----------------------------

⬜ LangGraph
⬜ MCP
⬜ GraphRAG
⬜ CRAG
⬜ Multi-agent workflows
⬜ SQL + RAG
⬜ Web search integration

Later, when you deploy, you replace the local Ollama process with a scalable inference backend (multiple GPU workers behind a load balancer). The rest of your architecture—the API, retrieval pipeline, orchestration, and indexing—can remain largely unchanged. That's why separating responsibilities, as you've done, is so valuable: the inference engine can evolve independently of the rest of the system.



This is a **battle-tested, production-grade architectural pattern** for FastAPI applications—especially those combining heavy document-reader UI features with asynchronous RAG background processing.

By isolating your API routes into domain-specific capabilities and introducing a clean `services/` layer, you establish hard boundaries that prevent your business logic, ML pipelines, and database operations from bleeding into HTTP handlers.

---

## Architectural Mapping

```
                         ┌─────────────────────────┐
                         │   Next.js Frontend      │
                         └────────────┬────────────┘
                                      │ HTTP / REST
                                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ API Layer (app/api/)                                                     │
│ Validate Requests ➔ Auth ➔ Call Service ➔ Return Schemas                 │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Service Layer (app/services/)                                            │
│ Business Logic ➔ DB Transactions ➔ Publish Events                        │
└──────────────┬───────────────────────────────┬───────────────────────────┘
               │                               │
               │ Publish Message               │ Direct Read / Write
               ▼                               ▼
┌──────────────────────────────┐              ┌────────────────────────────┐
│ Messaging (app/messaging/)   │              │ Database & Vector Storage  │
│ RabbitMQ Exchanges / Queues  │              │ PostgreSQL / SQLite        │
└──────────────┬───────────────┘              │ Qdrant / Tantivy           │
               │                              └────────────────────────────┘
               │ Consume Job                                 ▲
               ▼                                             │
┌──────────────────────────────┐                             │ Index / Store
│ Background Worker            │                             │
│ app/workers/ingestion_worker │                             │
└──────────────┬───────────────┘                             │
               │                                             │
               │ Execute                                     │
               ▼                                             │
┌────────────────────────────────────────────────────────────┴─────────────┐
│ Ingestion Pipeline (app/pipeline/ingestion/)                             │
│ OCR ➔ Extraction ➔ Cleaning ➔ Chunking ➔ Embedding ➔ Indexing            │
└──────────────────────────────────────────────────────────────────────────┘

```

---

## 3 Critical Implementation Rules for This Structure

### 1. Enforce Thin Routers

Routers must only handle **HTTP mechanics**: request validation, Pydantic schemas, Dependency Injection (`Depends`), and status codes.

```python
# app/api/documents_router.py
@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    # Router does NO business logic—it delegates directly to the service
    return await DocumentService.save_and_enqueue_document(file=file, db=db)

```

### 2. Service Layer Owns Database & Event Publishing

Services coordinate DB operations and event publishing. They should not know about FastAPI `Request` objects or background worker execution details.

```python
# app/services/document_service.py
class DocumentService:
    @staticmethod
    async def save_and_enqueue_document(file: UploadFile, db: AsyncSession) -> DocumentUploadResponse:
        # 1. Hash & Save raw file
        # 2. Persist 'pending' DB record
        # 3. Publish RabbitMQ job
        await publish_ingestion_job(document_id=doc.id, storage_key=doc.storage_key)
        return _to_response_schema(doc)

```

### 3. Workers Use Pipelines Directly, Not API Services

Workers consume from RabbitMQ and should invoke the **Pipeline layer** (`app/pipeline/ingestion/`) or specialized domain logic directly. Avoid calling API services from background workers to prevent cyclic dependencies and context leakage.

---

## Project Structure Overview

```text
app/
├── api/                       # HTTP API Boundary (Thin Routers)
│   ├── documents_router.py
│   ├── reader_router.py
│   ├── annotations_router.py
│   ├── bookmarks_router.py
│   ├── notes_router.py
│   ├── rag_router.py
│   ├── voice_router.py
│   └── user_state_router.py
│
├── services/                  # Business Logic & DB Coordination
│   ├── document_service.py
│   ├── reader_service.py
│   ├── annotation_service.py
│   ├── bookmark_service.py
│   ├── note_service.py
│   ├── rag_service.py
│   ├── voice_service.py
│   └── user_state_service.py
│
├── messaging/                 # RabbitMQ Producer & Topology
│   ├── connection.py
│   ├── exchanges.py
│   ├── queues.py
│   ├── publisher.py
│   └── messages.py
│
├── workers/                   # Async Consumers
│   ├── ingestion_worker.py
│   ├── ocr_worker.py
│   └── evaluation_worker.py
│
├── pipeline/                  # Core RAG / Processing Engine
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
├── models/                    # Database Models (SQLAlchemy)
├── schemas/                   # Pydantic Request/Response DTOs
└── config.py

```