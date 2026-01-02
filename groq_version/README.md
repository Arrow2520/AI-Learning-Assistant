# Project Documentation: DocMind (v2.0)

## 1. Project Overview

### Goal

Version 2 of the DocMind was built to **re-engineer the original system**
with a focus on:

- Cost efficiency
- Simpler deployment
- Reduced cloud lock-in
- Compatibility with free-tier infrastructure

The core user experience remains the same:

1. Upload PDF documents
2. Generate AI-powered summaries
3. Generate Q&A flashcards
4. Chat with documents using a RAG pipeline

However, the **internal architecture was significantly redesigned** compared to v1.

---

## 2. Why Version 2 Was Needed (Context from v1)

The initial implementation (v1) used:

- Google Gemini via Vertex AI
- Firebase Firestore for metadata and vector storage
- Firebase Storage for PDF files
- Google Cloud IAM, service accounts, and billing

While technically robust, v1 introduced challenges:

- Paid cloud dependencies for embeddings and inference
- Complex IAM and permission management
- Higher operational cost
- Not ideal for long-term free-tier deployment

As a result, **Version 2 focuses on achieving the same functionality with a leaner stack**.

---

## 3. Key Architectural Changes (v1 → v2)

| Component | Version 1 | Version 2 |
|---------|----------|----------|
| LLM | Google Gemini (Vertex AI) | Groq (LLaMA 3.1) |
| Embeddings | Vertex AI Embeddings | Local SentenceTransformers |
| Vector Store | Firebase Firestore | Supabase (Postgres + pgvector) |
| File Storage | Firebase Storage | Ephemeral local storage |
| Cost Model | Cloud billing | Minimal / free |

---

## 4. Tech Stack (Version 2)
- Backend: Flask (Python)
- LLM Inference: Groq API (LLaMA 3.1)
- Embeddings: SentenceTransformers (local CPU-based)
- Vector Database: Supabase (PostgreSQL + pgvector)
- Frontend: HTML, CSS, Vanilla JavaScript (Flask templates)
- Deployment: Render
- WSGI Server: Gunicorn


---

## 5. Phase 1: Backend Refactor & Environment Setup

### What We Did

- Preserved the original Gemini-based backend as v1
- Created a separate v2 backend implementation
- Removed all Firebase and Google Cloud dependencies
- Introduced environment-variable-based configuration
- Ensured compatibility with Render’s ephemeral filesystem

### Design Decision

Local file storage is used **only as a temporary buffer** for PDF processing.
Once embeddings are created, the system no longer depends on the raw PDF file.

---

## 6. Phase 2: PDF Processing & Text Chunking

### What We Did

- Reused the PDF extraction logic using `pypdf`
- Implemented chunking using `langchain-text-splitters`
- Standardized chunk size (1000 characters with overlap)
- Ensured chunking runs immediately after upload

This phase mirrors v1 logically but removes cloud storage dependency.

---

## 7. Phase 3: Local Embeddings & Vector Storage

### What We Did

- Integrated SentenceTransformers (`all-MiniLM-L6-v2`)
- Generated 384-dimensional embeddings locally
- Stored embeddings in Supabase using `pgvector`
- Implemented vector similarity search using `<->` operator

### Key Learning

PostgreSQL requires explicit casting when comparing vectors.
Query embeddings must be cast to `vector` type for similarity search.

---

## 8. Phase 4: AI Features (Groq-powered)

### Implemented Endpoints

- `/summarize/<doc_id>`
- `/generate_flashcards/<doc_id>`
- `/ask_question/<doc_id>` (RAG Chat)

### LLM Details

- Provider: Groq
- Model: `llama-3.1-8b-instant`
- Usage:
  - Document summarization
  - Flashcard generation
  - Context-aware question answering

Groq was chosen for:
- Extremely fast inference
- OpenAI-compatible API
- Generous free-tier access

---

## 9. Phase 5: RAG Chat Implementation

### What We Did

1. Embed user questions locally
2. Perform vector similarity search in Supabase
3. Retrieve top-k relevant chunks
4. Inject context into Groq prompt
5. Return grounded, document-aware responses

### Frontend

- Dedicated chat page (`chat.html`)
- JavaScript-based POST requests
- Clean separation between UI routes and API routes

---

## 10. Phase 6: Deployment to Render

### What We Did

- Created a dedicated `groq_version` directory
- Added `gunicorn` for production serving
- Configured Render Web Service with:
  - Root directory isolation
  - Environment variables for secrets
- Ensured stateless design compatible with ephemeral storage

This version runs **entirely on Render’s free tier**.

---

## 11. Key Learnings from Version 2

- Trade-offs between cloud-native and local-first AI systems
- Practical RAG implementation using PostgreSQL
- Handling vector similarity search correctly
- Designing AI systems under cost constraints
- Making deployment-safe architectural decisions

---

## 12. Project Status

Version 2 is **actively deployed and functional**.

Version 1 (Gemini + Google Cloud) has been preserved for reference but disabled due to
cloud billing constraints.

---

## 13. References & Documentation

- Groq API Documentation  
  https://console.groq.com/docs

- SentenceTransformers  
  https://www.sbert.net/

- Supabase Documentation  
  https://supabase.com/docs

- pgvector Extension  
  https://github.com/pgvector/pgvector

- Render Deployment Docs  
  https://docs.render.com/

---

## Final Note

This project intentionally preserves **both versions** to demonstrate
**architectural evolution, engineering trade-offs, and real-world system design**.
