# PrivateDoc RAG

PrivateDoc RAG is a self-hosted document intelligence system that lets users upload documents and ask grounded questions with source citations. It uses local LLM inference, local embeddings, vector search, and a full-stack web interface without relying on paid external AI APIs.

## Summary

This project is designed as a production-style RAG system, not a basic chatbot. It focuses on document ingestion, chunking, embeddings, semantic retrieval, citation-based answering, evaluation, and deployment.

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

## Project Goals

* Build a complete local RAG system
* Avoid paid external LLM APIs
* Make document Q&A more transparent with citations
* Evaluate retrieval and answer quality
* Deploy the system as a real full-stack AI application
* Demonstrate AI engineering, backend development, retrieval design, and deployment skills

## Planned API Endpoints

```text
GET    /health
POST   /documents/upload
GET    /documents
DELETE /documents/{document_id}
POST   /chat
GET    /evaluation
```

## Current Status

```text
Milestone 1: Backend skeleton
```

## Roadmap

* [ ] FastAPI backend setup
* [ ] Health endpoint
* [ ] Document upload
* [ ] PDF extraction
* [ ] Text chunking
* [ ] Local embeddings
* [ ] Qdrant vector storage
* [ ] Retrieval pipeline
* [ ] Local LLM generation
* [ ] Citation support
* [ ] Frontend upload page
* [ ] Frontend chat page
* [ ] Evaluation dashboard
* [ ] Docker deployment
* [ ] Demo video

## Summary

Built a self-hosted RAG document assistant using FastAPI, Next.js, Qdrant, Ollama, and Docker, enabling users to upload documents and receive grounded answers with source citations.
