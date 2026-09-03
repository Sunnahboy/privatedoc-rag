# PrivateDoc RAG

PrivateDoc RAG is a self-hosted, multimodal document intelligence workspace. It allows users to upload documents, select multiple files simultaneously, and ask grounded questions with real-time streaming answers, source citations, and visual page previews.

The system is designed around a privacy-first, enterprise-grade architecture: document processing, embeddings, retrieval, and LLM inference run entirely locally without sending sensitive data to external APIs.

It moves beyond basic LangChain prototypes by implementing a highly resilient, asynchronous, event-driven backend utilizing RabbitMQ for message brokering, Valkey for pub-sub streaming, and a Model-as-a-Service (MaaS) pattern for GPU fault isolation.

## Overview

PrivateDoc RAG focuses on the complete lifecycle of document-based question answering:

* **Multi-document workspace environments**
* **Document ingestion, OCR, and visual page extraction**
* **Centralized GPU-bound Model-as-a-Service (MaaS)** for embeddings
* **Query rewriting** and semantic intent distillation
* **Dense (Qdrant), Sparse (Tantivy), and Visual (ColQwen2)** retrieval
* **Reciprocal Rank Fusion (RRF)** & Cross-encoder reranking
* **Real-time token streaming** via Valkey (SSE)
* **Grounded LLM generation** with exact [Source, Page] citations
* **Asynchronous background ingestion** and distributed task workers

The primary goal is to demonstrate practical AI engineering, scalable backend architecture, multimodal information retrieval, and production-oriented system design.

## Core Features

### Document Ingestion

* Asynchronous distributed worker architecture.
* Document upload and validation with SHA-256 duplicate detection.
* PDF, DOCX, PPTX, Markdown, and TXT extraction.
* OCR for image-based PDFs and visual snapshot extraction.
* Text cleaning and recursive chunking.

### Retrieval Pipeline

* **Multi-Document Routing:** Dynamic vector filtering across selected document arrays (MatchAny & Boolean OR).
* **Query Rewriter:** Pre-retrieval LLM step to distill user intent into pure semantic keywords.
* **Hybrid Search:** Dense vector search (Qdrant) + Sparse keyword search (Tantivy/BM25).
* **Multimodal Search:** Visual search (ColQwen2 + Qdrant).
* **Reranking:** Reciprocal Rank Fusion (RRF) and FlashRank cross-encoder reranking.
* **Scaling:** Dynamic Top-K candidate scaling.

### Generation & UI

* **Real-time Streaming:** Server-Sent Events (SSE) token streaming via Valkey.
* **Local Inference:** Local LLM inference via Ollama.
* **Context Restriction:** Strict context-restricted generation to prevent cross-document hallucinations.
* **Workspace UI:** Next.js workspace UI with multi-select document grids.
* **Citations:** Inline source citations mapped to physical PDF pages.

### Infrastructure

* **Model-as-a-Service (MaaS):** Heavy GPU embedding models (FastEmbed/ColQwen2) are isolated in a centralized FastAPI microservice, preventing worker OOM crashes and freeing up I/O event loops.
* **Messaging:** RabbitMQ messaging with strict v2 queue topologies and TCP heartbeats for connection resiliency.
* **Persistence:** PostgreSQL for persistent chat history and metadata.
* **Indexing:** Qdrant (Dense/Visual) & Tantivy (Sparse) indexes.

## Tech Stack

| Layer | Technology |
| --- | --- |
| **Language** | Python 3.11 |
| **API / Backend** | FastAPI, Uvicorn, HTTPX |
| **Database** | PostgreSQL, SQLAlchemy, Alembic |
| **Vector Database** | Qdrant |
| **Sparse Search** | Tantivy / BM25 |
| **Fast Embeddings** | FastEmbed (ONNX Runtime) |
| **Visual Embeddings** | ColQwen2 |
| **LLM Inference** | Ollama |
| **Reranking** | FlashRank |
| **OCR / Extraction** | RapidOCR, PyMuPDF, python-docx, python-pptx |
| **Messaging** | RabbitMQ, aio-pika |
| **Stream Buffer** | Valkey (Redis API) |
| **Validation / Config** | Pydantic Settings |
| **Testing** | Pytest, pytest-asyncio |
| **Frontend** | Next.js, TypeScript, Tailwind CSS |
| **Deployment** | Docker, Nginx |

## Architecture

```text
                             ┌──────────────────┐
                             │      User        │
                             └────────┬─────────┘
                                      │ (SSE / HTTP)
                             ┌────────▼─────────┐
                             │  Next.js Client  │
                             └────────┬─────────┘
                                      │
                             ┌────────▼─────────┐
                             │   FastAPI API    │
                             └───────┬─┬─┬──────┘
                                     │ │ │
             ┌───────────────────────┘ │ └────────────────────────────┐
             │                         │ (SSE Stream)                 │
    ┌────────▼─────────┐      ┌────────▼─────────┐           ┌────────▼─────────┐
    │     RabbitMQ     │      │      Valkey      │◄──────────┤   PostgreSQL     │
    │ (Job Brokering)  │      │  (Pub/Sub Cache) │           │ (Chat & Metadata)│
    └────────┬─────────┘      └────────▲─────────┘           └────────▲─────────┘
             │                         │                              │
    ┌────────▼─────────┐      ┌────────┴─────────┐                    │
    │ Ingestion Worker │      │   Chat Worker    │────────────────────┘
    └────────┬─────────┘      └────────┬─────────┘
             │                         │
             │   ┌─────────────────────┴──────────────────────┐
             │   │             Query Rewriter                 │
             │   └─────────────────────┬──────────────────────┘
             │                         │
             │        ┌────────────────▼────────────────┐
             │        │        Hybrid Retrieval         │
             │        │ Qdrant (Dense) + Tantivy (BM25) │
             │        └────────────────┬────────────────┘
             │                         │
             │   ┌─────────────────────▼──────────────────────┐
             │   │       Reciprocal Rank Fusion (RRF)         │
             │   │        + FlashRank Cross-Encoder           │
             │   └─────────────────────┬──────────────────────┘
             │                         │
             │   ┌─────────────────────▼──────────────────────┐
             │   │             Ollama Generator               │
             │   │         (Tokens pushed to Valkey)          │
             │   └────────────────────────────────────────────┘
             │
             ▼
========================================================================
                      MODEL-AS-A-SERVICE (MaaS) TIER 
                 (GPU Isolated / ONNX Runtime Microservice)
========================================================================
    ┌────────────────┐         ┌────────────────┐
    │  FastEmbed API │         │ ColQwen2 API   │ 
    │ (Dense Vectors)│         │(Visual Vectors)│
    └────────────────┘         └────────────────┘

```