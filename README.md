# AI Learning Assistant

This repository contains an **AI-powered learning assistant** that allows users to upload PDF documents and interact with them using modern AI techniques such as **semantic search, chat, summaries, and flashcards**.

The project is intentionally structured to preserve **multiple architectural versions** of the same system, demonstrating **engineering evolution, design trade-offs, and real-world deployment considerations**.

---

## 📂 Repository Structure

```text
AI-Learning-Assistant/
├── gemini_version/
│   ├── app.py                # Flask application using Google Gemini API
│   ├── requirements.txt      # Dependencies for Gemini version
│   └── README.md             # Setup instructions for Gemini version
├── groq_version/
│   ├── app.py                # Flask application using Groq API
│   ├── requirements.txt      # Dependencies for Groq version
│   ├── templates/            # Frontend HTML files
│   │   ├── index.html        # Landing page
│   │   ├── chat.html         # AI Chat interface
│   │   ├── summary.html      # Content summarization view
│   │   └── flashcards.html   # Generated study aids
│   └── README.md             # Setup instructions for Groq version
├── .gitignore                # Files to ignore in Git (e.g., .env, venv)
└── README.md                 # Project overview and documentation
```


---

## 📁 Folder Explanations

### 🔹 `gemini_version/`
This folder contains **Version 1** of the project.

**Purpose:**
- Demonstrates a **cloud-native AI architecture**
- Uses Google Gemini and Google Cloud services
- Represents the initial implementation of the idea

**Why it exists:**
- Preserved intentionally to show:
  - Original design choices
  - Cloud-based AI integration
  - Comparison against later optimizations

Refer to `gemini_version/README.md` for full details.

---

### 🔹 `groq_version/`
This folder contains **Version 2** of the project.

**Purpose:**
- A complete **re-architecture** focused on:
  - Cost efficiency
  - Free-tier deployment
  - Reduced cloud lock-in
- Designed to be **production-deployable on Render**

**Key highlights:**
- LLM inference using Groq (LLaMA 3.1)
- Local embeddings using SentenceTransformers
- Vector search using Supabase (PostgreSQL + pgvector)
- Full RAG-based chat, summaries, and flashcards

This version is the **actively deployed and recommended implementation**.

Refer to `groq_version/README.md` for full details.

---

## 🧠 Why Two Versions?

This repository is structured to highlight **engineering decision-making**, not just functionality.

| Aspect | Gemini Version | Groq Version |
|-|---|-|
| Architecture | Cloud-heavy | Lean & portable |
| Cost | Paid cloud services | Free / minimal |
| Embeddings | Managed APIs | Local CPU-based |
| Goal | Feature completeness | Cost + deployability |

This evolution mirrors **real-world software engineering workflows**.

---

## 🚀 Features (Common Across Versions)

- PDF upload and processing
- Text chunking
- Semantic search using vector similarity
- AI-powered summaries
- Flashcard generation
- Context-aware chat (RAG)

---

## 🏗️ Deployment

- **Version 2 (Groq)** is designed for deployment on **Render**
- Uses ephemeral storage safely
- Stateless architecture after embeddings are created

---

## 📌 Notes

- Secrets (`.env`) are intentionally excluded from version control
- IDE-specific files are ignored via `.gitignore`
- Both versions are preserved for educational and evaluative purposes

---

## 📖 Further Documentation

- See `gemini_version/README.md` for the cloud-based implementation
- See `groq_version/README.md` for the optimized, deployable implementation

---

## ✨ Final Thought

This project is not just about building an AI application —  
it is about **understanding trade-offs, scalability, cost, and deployment realities**.

Both versions together tell the **full engineering story**.
