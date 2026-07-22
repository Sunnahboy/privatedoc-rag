# PrivateDoc RAG

PrivateDoc RAG is a self-hosted document intelligence system that lets users upload documents and ask grounded questions with source citations. It uses local LLM inference, local embeddings, vector search, and a full-stack web interface without relying on paid external AI APIs.

## Summary

This project is designed as a production-style Retrieval-Augmented Generation system, not a basic chatbot. It focuses on document ingestion, text extraction, chunking, embedding generation, semantic retrieval, citation-based answering, evaluation, and deployment.

The goal is to build a practical AI engineering project that demonstrates backend development, retrieval design, local AI inference, full-stack integration, and production-style deployment.

## Core Features

* Document upload
* PDF text extraction
* Text cleaning and chunking
* Local embedding generation
* Vector search with Qdrant
* Local LLM answering with Ollama
* Source citations
* Source preview
* FastAPI backend
* Next.js frontend
* Docker-based deployment
* RAG evaluation workflow

## Tech Stack

* Python
* FastAPI
* Next.js
* TypeScript
* Qdrant
* Ollama
* PostgreSQL
* Docker
* Nginx

## Architecture

```text
User
  ↓
Next.js Frontend
  ↓
FastAPI Backend
  ↓
RAG Pipeline
  ├── Document Parser
  ├── Text Cleaner
  ├── Chunker
  ├── Embedder
  ├── Vector Database
  ├── Retriever
  ├── Prompt Builder
  └── Local LLM Generator
        ↓
Answer + Citations + Sources
```

## RAG Pipeline

The system follows two main phases.

### 1. Indexing Phase

```text
Document Upload
  ↓
File Validation
  ↓
Text Extraction
  ↓
Text Cleaning
  ↓
Chunking
  ↓
Local Embedding Generation
  ↓
Vector Storage in Qdrant
  ↓
Metadata Storage
```

### 2. Query Phase

```text
User Question
  ↓
Question Embedding
  ↓
Vector Search
  ↓
Relevant Chunk Retrieval
  ↓
Grounded Prompt Construction
  ↓
Local LLM Generation
  ↓
Answer + Citations + Source Preview
```

## Project Goals

* Build a complete local RAG system
* Avoid paid external LLM APIs
* Make document Q&A more transparent with citations
* Evaluate retrieval and answer quality
* Deploy the system as a real full-stack AI application
* Demonstrate AI engineering, backend development, retrieval design, and deployment skills

## Planned API Endpoints

```text
GET     /health
POST    /documents/upload
GET     /documents
DELETE  /documents/{document_id}
POST    /chat
GET     /evaluation
```

## Current Status

**Milestone 1: Backend Skeleton**

The project is currently in the initial backend setup stage. The first milestone focuses on creating a clean FastAPI structure with configuration, logging, health checks, and documentation.

## Roadmap

* [ ] FastAPI backend setup
* [ ] Health endpoint
* [ ] Document upload
* [ ] PDF text extraction
* [ ] Text cleaning
* [ ] Text chunking
* [ ] Local embeddings
* [ ] Qdrant vector storage
* [ ] Retrieval pipeline
* [ ] Local LLM generation
* [ ] Citation support
* [ ] Source preview
* [ ] Frontend upload page
* [ ] Frontend chat page
* [ ] Evaluation dashboard
* [ ] Docker deployment
* [ ] Demo video

## Core File structure
PrivateDoc RAG

├── API Layer
│
├── Ingestion Pipeline
│      Upload
│      Extraction
│      Cleaning
│      Chunking
│      Embedding
│      Indexing
│
├── Retrieval Pipeline
│      Query Embedding
│      Hybrid Search
│      Metadata Filter
│      Reranking
│
├── Generation Pipeline
│      Prompt Builder
│      LLM
│      Citations
│
├── Infrastructure
│      Database
│      Qdrant
│      Ollama
│      Logging
│      Config
│
└── Evaluation & Monitoring
       Metrics
       Benchmarks
       Observability

## Advanced Roadmap

After the standard RAG pipeline works, the system may be extended with:

* CAG-inspired caching for repeated questions and document summaries.
* CRAG-inspired retrieval confidence checking for dynamic evaluation.
* GraphRAG-style relationship extraction and entity-based retrieval.
* KAG-inspired mutual indexing linking unstructured text to structured knowledge.
* KAG logical reasoning using semantic graphs for multi-step queries.
* Hybrid search using both vector search and keyword search.
* Reranking for better retrieval quality.
* Developer debug mode showing retrieved chunks, similarity scores, and latency.

## Why This Project Matters

Many AI demos only show a chatbot interface. PrivateDoc RAG is designed to go deeper by showing how an AI system is engineered end-to-end:

* How documents are processed
* How knowledge is chunked and indexed
* How embeddings are generated locally
* How relevant context is retrieved
* How answers are grounded in sources
* How hallucination risk is reduced
* How retrieval quality is evaluated
* How the system is deployed

## License

This project is currently under active development.
