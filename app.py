import base64
import requests
import os
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from dotenv import load_dotenv  # Load environment variables

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Get API key from environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("❌ Error: GEMINI_API_KEY is missing! Set it in a .env file.")

# Gemini API endpoint
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

# Store uploaded images temporarily
image_store = {}

def send_to_gemini(image_path, prompt):
    """Send image with a prompt to Gemini API."""
    with open(image_path, "rb") as img_file:
        image_base64 = base64.b64encode(img_file.read()).decode("utf-8")

    headers = {"Content-Type": "application/json"}
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": image_base64
                        }
                    },
                    {"text": prompt}
                ]
            }
        ]
    }

    response = requests.post(GEMINI_API_URL, headers=headers, json=payload)

    if response.status_code == 200:
        try:
            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return "No valid response from API."
    else:
        return f"Error: {response.status_code} - {response.text}"

def format_description(description):
    """Convert description into an organized format."""
    lines = description.split(". ")  # Split into sentences
    formatted = "<ul>"  # Start an unordered list
    for line in lines:
        if line.strip():
            formatted += f"<li>{line.strip()}.</li>"  # Add each sentence as a list item
    formatted += "</ul>"
    return formatted

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    """Handles image upload and generates an organized description."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Store the latest uploaded image path
    image_store['latest'] = filepath

    # Generate an organized description
    raw_description = send_to_gemini(filepath, "Describe this image in detail, providing key points rather than a paragraph.")
    formatted_description = format_description(raw_description)

    return jsonify({'message': 'Image uploaded successfully', 'filename': filename, 'description': formatted_description})

@app.route('/ask', methods=['POST'])
def ask_question():
    """Processes the user's question using the uploaded image."""
    data = request.json
    question = data.get("question", "").strip()

    if not question:
        return jsonify({'error': 'Question cannot be empty'}), 400

    image_path = image_store.get('latest')
    if not image_path:
        return jsonify({'error': 'No image uploaded'}), 400

    # Ask the question explicitly
    answer = send_to_gemini(image_path, f"Analyze this image and answer the following question: {question}")

    return jsonify({'answer': answer})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

