import os
import uuid
import psycopg2
import requests
import markdown2
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

# --------------------------------------------------
# ENV
# --------------------------------------------------
load_dotenv()

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --------------------------------------------------
# DB
# --------------------------------------------------
conn = psycopg2.connect(SUPABASE_DB_URL)
conn.autocommit = True

# --------------------------------------------------
# LOCAL EMBEDDINGS
# --------------------------------------------------
embedder = SentenceTransformer("all-MiniLM-L6-v2")

def embed_text(text):
    return embedder.encode(text).tolist()

# --------------------------------------------------
# GROQ LLM
# --------------------------------------------------
HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

def groq_generate(prompt):
    res = requests.post(
        f"{GROQ_BASE_URL}/chat/completions",
        headers=HEADERS,
        json={
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": "You are a helpful AI learning assistant."},
                {"role": "user", "content": prompt}
            ]
        }
    )

    if res.status_code != 200:
        raise RuntimeError(f"Groq error: {res.text}")

    return res.json()["choices"][0]["message"]["content"]

# --------------------------------------------------
# PDF UTILS
# --------------------------------------------------
def extract_text_from_pdf(path):
    reader = PdfReader(path)
    return "\n".join(
        page.extract_text()
        for page in reader.pages
        if page.extract_text()
    )

# --------------------------------------------------
# FLASK
# --------------------------------------------------
app = Flask(__name__)
CORS(app)

# --------------------------------------------------
# ROUTES
# --------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload_pdf", methods=["POST"])
def upload_pdf():
    try:
        pdf = request.files.get("pdf_file")
        if not pdf:
            return jsonify({"error": "No PDF uploaded"}), 400

        doc_id = str(uuid.uuid4())
        filename = f"{doc_id}_{pdf.filename}"
        path = os.path.join(UPLOAD_FOLDER, filename)
        pdf.save(path)

        cur = conn.cursor()
        cur.execute(
            "INSERT INTO documents (id, user_id, file_name) VALUES (%s,%s,%s)",
            (doc_id, "temp_user", filename)
        )

        text = extract_text_from_pdf(path)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        chunks = splitter.split_text(text)

        for chunk in chunks:
            emb = embed_text(chunk)
            cur.execute(
                "INSERT INTO embeddings (document_id, content, embedding) VALUES (%s,%s,%s)",
                (doc_id, chunk, emb)
            )

        return jsonify({
            "status": "success",
            "document_id": doc_id
        })

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/summarize/<doc_id>")
def summarize(doc_id):
    cur = conn.cursor()
    cur.execute(
        "SELECT content FROM embeddings WHERE document_id=%s LIMIT 10",
        (doc_id,)
    )
    text = " ".join(row[0] for row in cur.fetchall())

    prompt = f"Summarize the following content clearly:\n{text}"
    summary = groq_generate(prompt)

    return render_template(
        "summary.html",
        summary_html=markdown2.markdown(summary)
    )

@app.route("/generate_flashcards/<doc_id>")
def generate_flashcards(doc_id):
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT content FROM embeddings WHERE document_id=%s LIMIT 12",
            (doc_id,)
        )
        text = " ".join(row[0] for row in cur.fetchall())

        if not text.strip():
            raise RuntimeError("No content available to generate flashcards.")

        prompt = f"""
You are an AI that ONLY outputs valid JSON.
DO NOT include explanations, markdown, or extra text.

Task:
Generate 8 flashcards from the text below.

Output format (STRICT):
[
  {{"question": "Q1", "answer": "A1"}},
  {{"question": "Q2", "answer": "A2"}}
]

Text:
{text}
"""

        response = groq_generate(prompt).strip()

        # --- SAFE JSON EXTRACTION ---
        import json, re

        match = re.search(r"\[.*\]", response, re.DOTALL)
        if not match:
            raise RuntimeError("Model did not return valid JSON.")

        json_text = match.group()
        flashcards = json.loads(json_text)

        for card in flashcards:
            card["question"] = markdown2.markdown(card["question"])
            card["answer"] = markdown2.markdown(card["answer"])

        return render_template(
            "flashcards.html",
            flashcards=flashcards
        )

    except Exception as e:
        print("FLASHCARD ERROR:", e)
        return render_template(
            "flashcards.html",
            flashcards=[{
                "question": "Error generating flashcards",
                "answer": str(e)
            }]
        )


@app.route("/ask_question/<doc_id>", methods=["POST"])
def ask_question(doc_id):
    question = request.json.get("question")
    if not question:
        return jsonify({"error": "No question"}), 400

    q_emb = str(embed_text(question))

    cur = conn.cursor()
    cur.execute("""
        SELECT content
        FROM embeddings
        WHERE document_id = %s
        ORDER BY embedding <-> %s::vector
        LIMIT 5
    """, (doc_id, q_emb))

    context = "\n\n".join(row[0] for row in cur.fetchall())

    prompt = f"""
    Answer ONLY using the context below.
    If the answer is not present, say you don't know or the question asked is irrelevant to the PDF uploaded.

    Context:
    {context}

    Question:
    {question}
    """

    answer = groq_generate(prompt)

    return jsonify({
        "status": "success",
        "answer": markdown2.markdown(answer)
    })

@app.route("/chat/<doc_id>")
def chat_page(doc_id):
    return render_template("chat.html")

# --------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
