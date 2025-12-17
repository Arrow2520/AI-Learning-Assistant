# Project Documentation: AI Learning Assistant (v1.0)

## 1. Project Overview

### Goal

To build a full-stack, AI-powered web application where users can upload PDF documents and
interact with them in three ways:

1. Generate AI-powered summaries.
2. Generate AI-powered Q&A flashcards.
3. Engage in an interactive, context-aware chat (RAG).

### Tech Stack

```
● Backend: Flask (Python)
● Database: Firebase Firestore (for metadata and vector storage)
● File Storage: Firebase Storage
● AI Models: Google Cloud Vertex AI (Gemini 2.5 Pro for generation, Text-Embedding-
for embeddings)
● Frontend: HTML, CSS, vanilla JavaScript (served via Flask templates)
● Deployment: Render
● Key Libraries: google-cloud-aiplatform, firebase-admin, pypdf, langchain-text-splitters,
gunicorn
```
## 2. Phase 1: Backend Setup & Firebase Initialization

### What We Did

● Set up a Python 3.11 virtual environment (.venv).\
● Initialized a new Firebase project, enabling Firestore , Storage , and Authentication.
● Created a new Flask application (app.py).\
● Installed core libraries: flask, firebase-admin, google-cloud-storage, python-dotenv.\
● Downloaded a serviceAccountKey.json file from Firebase to provide the backend server
with admin access to the project.\
● Created a .env file to securely store all secret keys.

### Challenge: Securing Secret Keys


● Problem: The `serviceAccountKey.json` and any API keys are secrets and must not be
committed to a public GitHub repository.\
● Solution: We created a `.gitignore` file and added .`env`,` serviceAccountKey.json`, and .`venv/`
to it. This tells Git to ignore these files, so they never get pushed to the repository.


## 3. Phase 2: PDF Upload & Text Extraction

### What We Did


● Built the /upload_pdf API endpoint in Flask.\
● This endpoint receives a file from a simple HTML form and performs two critical actions:

1. **Firebase Storage:** Saves the raw PDF file to a unique path in our Firebase Storage
    bucket.
2. **Firestore:** Saves a metadata record (filename, storage path, user ID) in a documents
    collection in Firestore.\

● Wrote a helper function, `extract_text_from_pdf`, using the `pypdf` library. This function
takes a `document_id`, finds its path in Firestore, downloads the file from Storage into
memory, and returns all its text as a single string.

### Challenge: Firebase Storage "Bucket Not Found"


● Problem: Our first upload test failed with a 404: Bucket does not exist error.\

● Solution: The error was twofold:

1. We had not "activated" the storage bucket in the Firebase console. We had to go to
    the Storage tab and click "Get Started."
2. The bucket name in our firebase_admin.initialize_app config was incorrect. We
    updated it to the correct ai-learning-assistant-ba60f.firebasestorage.app address
    shown in the console.


## 4. Phase 3: AI Summaries & Flashcards

### What We Did


● Built the `/summarize/<doc_id>` and `/generate_flashcards/<doc_id>` API endpoints.\
● These endpoints re-use our `extract_text_from_pdf` function to get the document's
content.\
● We crafted specific prompts for each feature (e.g., "Provide a concise summary..." and
"Generate a JSON array of flashcards...").\
● The results are passed to new HTML templates (`summary.html`, `flashcards.html`) and
rendered to the user.

### Challenge: The "403 Permission Denied" & "404 Model Not Found"

### Saga

This was our most complex challenge, as it involved multiple layers of Google Cloud
permissions.\

● **Problem 1:** Even with billing enabled, our API calls to Gemini were failing with 404 Model
not found. We tried `gemini-2.5-pro` and `gemini-pro` with the same result.

● **Solution 1 (Switching SDKs):** We diagnosed that authenticating with a simple API key
(google-generativeai library) was failing. We switched to the more robust **Vertex AI SDK**
(google-cloud-aiplatform). This library authenticates using our serviceAccountKey.json
file, which is the standard for backend servers.

● Problem 2: After switching, we got a new error: 403 Permission Denied:
aiplatform.endpoints.predict.

● Solution 2 (IAM Permissions): This was the breakthrough. The error meant our service
account (originally for Firebase) didn't have permission to use Vertex AI. We fixed this by:
1. Going to the **Google Cloud IAM & Admin** page.
2. Finding our Firebase service account (e.g.,
    firebase-adminsdk-...@...gserviceaccount.com).
3. Granting it the **"Vertex AI User"** role. This gave it the necessary permissions, and our
    AI features instantly started working.

## 5. Phase 4: RAG Chatbot (Embeddings & Vector

## Search)

This was the final and most advanced feature, building a full Retrieval-Augmented Generation
(RAG) pipeline.

### What We Did

1. **Chunking:** We used langchain-text-splitters to break the PDF text into small,
    1000-character chunks.
2. **Embeddings:** We initialized a TextEmbeddingModel from Vertex AI.
3. **Storage:** We created a new function create_and_store_embeddings that runs _after_ every
    PDF upload. It loops through each text chunk, generates a vector embedding for it, and
    saves it to a new subcollection in Firestore: documents/{doc_id}/embeddings/{chunk_id}.
4. **Chat API:** We built the final /ask_question API. This endpoint:
    ○ Gets the user's question.
    ○ Generates an embedding for the question.
    ○ Uses Firestore's find_nearest function to do a **vector search** on our new index.
    ○ Builds a new prompt containing the user's question + the most relevant text chunks.
    ○ Sends this to Gemini to get a final, context-aware answer.
5. **Frontend:** We built chat.html with a JavaScript-powered chat interface that calls our
    /ask_question API.

### Challenges Faced & Solutions


● Problem 1: 404 Model not found for the embedding model
(`textembedding-gecko@003`).

● Solution 1: The first model we tried was unavailable to our project. We switched to the
newer text-embedding-004 model, which resolved the error.

● Problem 2: ImportError: cannot import name 'Vector' from
'google.cloud.firestore_v1.types'.\

● Solution 2: The import path had changed in a recent library update. We found the
correct path: from google.cloud.firestore_v1.vector import Vector.

● Problem 3: We couldn't find a way to create the Vector Index in the Firestore console UI.

● Solution 3: After research, we discovered that this feature must be created via the
command line. We installed the gcloud CLI and successfully built the index with the
command:
gcloud firestore indexes composite create \
--collection-group=embeddings \
--query-scope=COLLECTION \
--field-config=field-path=embedding,vector-config='{"dimension":768,"flat":"{}"}'


## 6. Phase 5: Deployment to Render

### What We Did


● Generated a requirements.txt file using pip freeze > requirements.txt.
● Pushed our safe code (using .gitignore) to a new GitHub repository.
● Created a new "Web Service" on Render.com and linked it to our GitHub repo.

### Challenges Faced & Solutions


● Problem 1: How to provide the `serviceAccountKey.json` and `.env` variables to the live
server.

● Solution 1: We used Render's "Environment" tab:

○ Secret Files: We created a secret file named serviceAccountKey.json and pasted the
entire contents of our local key file into it.\
○ Environment Variables: We added GOOGLE_APPLICATION_CREDENTIALS (with the
value serviceAccountKey.json), PYTHON_VERSION, and USE_MOCK_AI.

● Problem 2: The initial deployment failed due to the Python version.

● Solution 2: Render's logs showed it requires a full patch version. We changed the
PYTHON_VERSION variable from 3.11 to 3.11.9 , which fixed the build.


**Note: ** Project Status: This project has been disabled for now due to budget constraints and billing charges on Firebase and Google Cloud. 
I am currently exploring various workarounds and optimizations to minimize costs and bring the service back online soon.