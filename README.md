# PrivateDoc RAG

PrivateDoc RAG is a self-hosted document intelligence system for uploading documents and asking grounded questions with source citations and previews.

The system is designed around a privacy-first architecture: document processing, embeddings, retrieval, and LLM inference can run locally without sending document content to external AI APIs.

It is built as a production-style Retrieval-Augmented Generation (RAG) system rather than a basic chatbot, with separate ingestion, retrieval, generation, messaging, and infrastructure components.

## Overview

PrivateDoc RAG focuses on the complete lifecycle of document-based question answering:

- Document ingestion and validation
- Duplicate document detection
- Text extraction and OCR
- Text cleaning and chunking
- Local embedding generation
- Dense and sparse retrieval
- Reciprocal Rank Fusion (RRF)
- Cross-encoder reranking
- Grounded LLM generation
- Source citations and previews
- Performance profiling
- Quantitative RAG evaluation
- Asynchronous background ingestion

The primary goal is to demonstrate practical AI engineering, backend architecture, information retrieval, local AI inference, and production-oriented system design.

## Core Features

### Document Ingestion

- Document upload and validation
- SHA-256 content hashing for duplicate detection
- PDF, DOCX, PPTX, Markdown, and TXT extraction
- OCR for image-based PDF pages
- Text cleaning
- Recursive chunking
- Metadata tracking
- Asynchronous ingestion architecture

### Retrieval

- Dense vector search with Qdrant
- Sparse keyword search with Tantivy/BM25
- Hybrid retrieval
- Reciprocal Rank Fusion (RRF)
- Cross-encoder reranking with FlashRank
- Top-K context selection

### Generation

- Local LLM inference with Ollama
- Grounded prompt construction
- Context-restricted generation
- Source citations
- Source previews
- Configurable generation model

### Infrastructure

- FastAPI backend
- PostgreSQL metadata storage
- Qdrant vector database
- Tantivy sparse index
- RabbitMQ messaging
- Background ingestion workers
- Docker-based deployment
- Nginx
- Centralized configuration
- Structured logging
- Pipeline profiling

### Evaluation & Observability

- Retrieval metrics
- Answer quality evaluation
- Pipeline latency profiling
- Retrieval and generation timing
- Debug information for retrieved chunks and scores

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| Frontend | Next.js, TypeScript |
| LLM Runtime | Ollama |
| Embeddings | Ollama |
| Vector Search | Qdrant |
| Sparse Search | Tantivy / BM25 |
| Reranking | FlashRank |
| Database | PostgreSQL |
| Messaging | RabbitMQ |
| OCR | RapidOCR / ONNX Runtime |
| Deployment | Docker, Nginx |

## Architecture

```text
                         ┌──────────────────┐
                         │      User        │
                         └────────┬─────────┘
                                  │
                         ┌────────▼─────────┐
                         │  Next.js Client  │
                         └────────┬─────────┘
                                  │
                         ┌────────▼─────────┐
                         │   FastAPI API    │
                         └───────┬─┬────────┘
                                 │ │
                 ┌───────────────┘ └────────────────┐
                 │                                  │
        ┌────────▼─────────┐              ┌─────────▼─────────┐
        │ Document Ingest │              │   RAG Retrieval   │
        └────────┬─────────┘              └─────────┬─────────┘
                 │                                  │
        ┌────────▼─────────┐              ┌─────────▼─────────┐
        │    RabbitMQ      │              │  Query Embedding  │
        └────────┬─────────┘              └─────────┬─────────┘
                 │                                  │
        ┌────────▼─────────┐              ┌─────────▼─────────┐
        │ Background Worker│              │ Hybrid Retrieval  │
        └────────┬─────────┘              │ Qdrant + Tantivy  │
                 │                        └─────────┬─────────┘
        ┌────────▼─────────┐                        │
        │ File Extraction  │              ┌─────────▼─────────┐
        │ + OCR             │              │    RRF Fusion     │
        └────────┬─────────┘              └─────────┬─────────┘
                 │                                  │
        ┌────────▼─────────┐              ┌─────────▼─────────┐
        │ Cleaning         │              │ FlashRank Reranker │
        │ Chunking         │              └─────────┬─────────┘
        │ Embedding        │                        │
        │ Indexing         │              ┌─────────▼─────────┐
        └──────────────────┘              │ Context Selection │
                                          └─────────┬─────────┘
                                                    │
                                          ┌─────────▼─────────┐
                                          │ Ollama Generator  │
                                          └─────────┬─────────┘
                                                    │
                                          ┌─────────▼─────────┐
                                          │ Answer + Citations│
                                          └───────────────────┘