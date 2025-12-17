import os
import uuid
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore, storage
from datetime import datetime
from PyPDF2 import PdfReader
import io
import vertexai
from vertexai.generative_models import GenerativeModel
from langchain_text_splitters import RecursiveCharacterTextSplitter
from vertexai.language_models import TextEmbeddingModel
from google.cloud.firestore_v1.vector import Vector
import time
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
import markdown2

# Load environment variables from .env file
load_dotenv()

# --- Firebase Initialization ---
try:
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not os.path.exists(cred_path):
        raise FileNotFoundError(f"Service account key not found at: {cred_path}")

    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'ai-learning-assistant-ba60f.firebasestorage.app'
    })
    db = firestore.client()
    bucket = storage.bucket()
    print("Firebase connection successful!")
except Exception as e:
    print(f"Firebase connection failed: {e}")
    db = None
    bucket = None
# -----------------------------

# --- Vertex AI (Gemini) Initialization ---
try:
    PROJECT_ID = "ai-learning-assistant-ba60f"
    LOCATION = "us-central1"
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    # Model for text generation (summaries, flashcards, chat)
    model = GenerativeModel("gemini-2.5-pro")
    print("Vertex AI (Gemini) initialized successfully!")
except Exception as e:
    print(f"Vertex AI initialization failed: {e}")
    model = None
# -----------------------------

# --- Initialize the Embedding Model ---
try:
    # Use the official Google model for text embeddings
    embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
    print("Text Embedding model initialized successfully!")
except Exception as e:
    print(f"Text Embedding model initialization failed: {e}")
    embedding_model = None


# ------------------------------------

def extract_text_from_pdf(document_id):
    """
    Downloads a PDF from Firebase Storage, extracts its text, and returns it.
    """
    try:
        # 1. Get the document metadata from Firestore
        doc_ref = db.collection('documents').document(document_id)
        doc_snapshot = doc_ref.get()

        if not doc_snapshot.exists:
            print(f"Error: Document with ID {document_id} not found in Firestore.")
            return None

        # 2. Get the file path
        storage_path = doc_snapshot.to_dict().get('storage_path')
        if not storage_path:
            print(f"Error: storage_path not found for document {document_id}.")
            return None

        # 3. Download the file from Firebase Storage into memory
        blob = bucket.blob(storage_path)
        pdf_content_in_memory = io.BytesIO(blob.download_as_bytes())
        print(f"Successfully downloaded {storage_path} from Firebase Storage.")

        # 4. Use PyPDF2 to read the in-memory PDF
        pdf_reader = PdfReader(pdf_content_in_memory)

        # 5. Extract text from each page
        full_text = ""
        for page in pdf_reader.pages:
            full_text += page.extract_text() + "\n"

        print(f"Successfully extracted {len(full_text)} characters of text.")
        return full_text

    except Exception as e:
        print(f"An error occurred in extract_text_from_pdf: {e}")
        return None


# --- Function to create and store embeddings ---
def create_and_store_embeddings(document_id, text_content):
    """
    Chunks text, creates embeddings, and stores them in Firestore.
    This is a one-time process per document.
    """
    if not embedding_model:
        print("Error: Embedding model is not initialized.")
        return False

    try:
        # 1. Chunk the text
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,  # Max 1000 characters per chunk
            chunk_overlap=100  # 100 characters of overlap
        )
        chunks = text_splitter.split_text(text_content)
        print(f"Text chunked into {len(chunks)} pieces.")

        # 2. Create embeddings and store in Firestore
        batch = db.batch()
        # Create a new subcollection for this document's embeddings
        embeddings_collection = db.collection('documents').document(document_id).collection('embeddings')

        for i, chunk in enumerate(chunks):
            # 3. Get the vector embedding from the Google AI model
            # Note: The API has a limit of 5 requests per second
            time.sleep(0.2)  # 200ms delay to respect rate limits
            response = embedding_model.get_embeddings([chunk])
            embedding_vector = response[0].values

            # 4. Create a new document in the "embeddings" subcollection
            doc_ref = embeddings_collection.document(f"chunk_{i}")
            batch.set(doc_ref, {
                'text_chunk': chunk,
                'embedding': Vector(embedding_vector)  # Use the Vector type
            })

        # 5. Commit the batch
        batch.commit()
        print(f"Successfully stored {len(chunks)} embeddings in Firestore.")

        # 6. Update the main document's status
        doc_ref = db.collection('documents').document(document_id)
        doc_ref.update({'status': 'processed'})  # Mark as processed
        return True

    except Exception as e:
        print(f"An error occurred in create_and_store_embeddings: {e}")
        return False


# ----------------------------------------------------

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app)


# ------------------------------

# --- API Routes ---
@app.route('/')
def index():
    return render_template('index.html')

# --- ADD THIS NEW ROUTE ---
@app.route('/chat/<string:doc_id>')
def chat_page(doc_id):
    # This renders the chat.html page
    return render_template('chat.html')
# --------------------------

# --- UPDATED: /upload_pdf function ---
@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    if 'pdf_file' not in request.files:
        return jsonify({"status": "error", "message": "No PDF file found in request"}), 400

    pdf_file = request.files['pdf_file']
    if pdf_file.filename == '':
        return jsonify({"status": "error", "message": "No file selected"}), 400

    if pdf_file and pdf_file.filename.endswith('.pdf'):
        try:
            doc_id = str(uuid.uuid4())
            user_id = "temp_user_id_123"

            file_path = f"uploads/{user_id}/{doc_id}/{pdf_file.filename}"
            blob = bucket.blob(file_path)
            blob.upload_from_file(pdf_file, content_type='application/pdf')

            # 6. Create document record
            doc_ref = db.collection('documents').document(doc_id)
            doc_ref.set({
                'user_id': user_id,
                'file_name': pdf_file.filename,
                'storage_path': file_path,
                'created_at': datetime.utcnow(),
                'status': 'uploaded'  # Set initial status
            })

            # --- THIS IS THE NEW PART ---
            # 7. Start the embedding process
            print(f"Starting embedding process for {doc_id}...")
            text_content = extract_text_from_pdf(doc_id)
            if text_content:
                create_and_store_embeddings(doc_id, text_content)
            else:
                print(f"Could not extract text for {doc_id} to create embeddings.")
            # ---------------------------

            # 8. Return success response
            return jsonify({
                "status": "success",
                "message": "PDF uploaded and processing started!",  # Updated message
                "document_id": doc_id
            }), 201

        except Exception as e:
            return jsonify({"status": "error", "message": f"An error occurred: {e}"}), 500
    else:
        return jsonify({"status": "error", "message": "Invalid file type. Only PDFs are allowed."}), 400


# ---------------------------------------

@app.route('/get_text/<string:doc_id>', methods=['GET'])
def get_pdf_text(doc_id):
    """A simple endpoint to test our text extraction function."""
    extracted_text = extract_text_from_pdf(doc_id)
    if extracted_text:
        return jsonify({
            "status": "success",
            "document_id": doc_id,
            "character_count": len(extracted_text),
            "extracted_text_preview": extracted_text[:500] + "..."
        })
    else:
        return jsonify({
            "status": "error",
            "message": "Failed to extract text. Check server logs for details."
        }), 500


@app.route('/summarize/<string:doc_id>', methods=['GET'])
def summarize_pdf(doc_id):
    if os.getenv("USE_MOCK_AI") == "True":
        print("🤖 Running in Mock AI mode.")
        mock_summary = "This is a mock summary..."
        return render_template('summary.html', summary_text=mock_summary)

    if not model:
        return render_template('summary.html', summary_text="Error: Gemini AI model is not initialized.")

    text = extract_text_from_pdf(doc_id)
    if not text:
        return render_template('summary.html', summary_text="Error: Failed to extract text from the PDF.")

    prompt = f"Provide a concise, easy-to-understand summary of the following text:\n\n{text}"

    try:
        response = model.generate_content(prompt)
        summary_html = markdown2.markdown(response.text)
        return render_template('summary.html', summary_html=summary_html)
    except Exception as e:
        error_message = f"An error occurred with the AI model: {e}"
        return render_template('summary.html', summary_html=error_message)


@app.route('/generate_flashcards/<string:doc_id>', methods=['GET'])
def generate_flashcards(doc_id):
    if os.getenv("USE_MOCK_AI") == "True":
        print("🤖 Running in Mock AI mode for Flashcards.")
        mock_flashcards = [
            {"question": "What is the capital of France?", "answer": "Paris"},
            {"question": "How many planets are in our solar system?", "answer": "Eight"},
        ]
        return render_template('flashcards.html', flashcards=mock_flashcards)

    if not model:
        return render_template('flashcards.html', flashcards=[])

    text = extract_text_from_pdf(doc_id)
    if not text:
        return render_template('flashcards.html', flashcards=[])

    prompt = f"""
    Based on the following text, generate a series of question and answer flashcards.
    Return the response as a valid JSON array of objects, where each object has a "question" key and an "answer" key.
    Text to analyze:
    {text}
    """

    try:
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        import json
        flashcards_data = json.loads(cleaned_response)

        # Convert question and answer fields from Markdown to HTML
        for card in flashcards_data:
            if 'question' in card:
                card['question'] = markdown2.markdown(card['question'])
            if 'answer' in card:
                card['answer'] = markdown2.markdown(card['answer'])
        # ----------------

        return render_template('flashcards.html', flashcards=flashcards_data)
    except Exception as e:
        print(f"Error generating or parsing flashcards: {e}")
        error_card = [{"question": "An error occurred", "answer": str(e)}]
        return render_template('flashcards.html', flashcards=error_card)


@app.route('/ask_question/<string:doc_id>', methods=['POST'])
def ask_question(doc_id):
    if not model or not embedding_model:
        return jsonify({"status": "error", "answer": "AI models are not initialized."}), 500

    # 1. Get the user's question from the JSON body
    data = request.json
    question = data.get('question')
    if not question:
        return jsonify({"status": "error", "answer": "No question provided."}), 400

    try:
        # 2. Embed the user's question using the same model
        question_embedding = embedding_model.get_embeddings([question])[0].values

        # 3. Find the most relevant text chunks from Firestore
        embeddings_collection = db.collection('documents').document(doc_id).collection('embeddings')

        # Use the find_nearest method to perform a vector search
        query = embeddings_collection.find_nearest(
            vector_field="embedding",
            query_vector=Vector(question_embedding),
            distance_measure=DistanceMeasure.EUCLIDEAN,  # Must match your index!
            limit=5  # Get the top 5 most relevant chunks
        )

        # Get the actual text from the documents
        relevant_chunks = [doc.to_dict()['text_chunk'] for doc in query.stream()]

        if not relevant_chunks:
            return jsonify({"status": "success",
                            "answer": "I'm sorry, I couldn't find any relevant information in the document to answer that."})

        # 4. Build a rich prompt for the AI
        context = "\n\n".join(relevant_chunks)
        prompt = f"""
        You are a helpful assistant. Answer the following question based ONLY on the provided context.
        If the answer is not in the context, say "I'm sorry, I couldn't find that information in the document."

        Context:
        {context}

        Question:
        {question}

        Answer:
        """

        # 5. Generate the answer from Gemini
        response = model.generate_content(prompt)
        answer_html = markdown2.markdown(response.text)

        return jsonify({
            "status": "success",
            "answer": answer_html
        })

    except Exception as e:
        print(f"An error occurred in /ask_question: {e}")
        return jsonify({"status": "error", "answer": f"An error occurred: {e}"}), 500

# This allows the file to be run directly
if __name__ == '__main__':
    app.run(debug=True, port=5000)