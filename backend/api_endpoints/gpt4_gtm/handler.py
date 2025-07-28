from flask import Blueprint, request, jsonify
from openai import OpenAI
import os
from werkzeug.utils import secure_filename
import PyPDF2
import pandas as pd
from docx import Document

gpt4_blueprint = Blueprint('gpt4', __name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL_NAME = "ft:gpt-4.1-mini-2025-04-14:personal::BvmGNtx5"


def extract_text_from_file(file_storage):
    filename = secure_filename(file_storage.filename)
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".txt":
        file_storage.seek(0)
        return file_storage.read().decode("utf-8")

    elif ext == ".pdf":
        file_storage.seek(0)
        reader = PyPDF2.PdfReader(file_storage)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text

    elif ext == ".docx":
        file_storage.seek(0)
        doc = Document(file_storage)
        return "\n".join([para.text for para in doc.paragraphs])

    elif ext == ".csv":
        file_storage.seek(0)
        df = pd.read_csv(file_storage)
        return df.to_string(index=False)

    else:
        raise ValueError("Unsupported file type.")

@gpt4_blueprint.route("/gtm/respond", methods=["POST"])
def generate_response_openai():
    try:
        prompt = ""
        file = None
        
        # If JSON request (no file)
        if request.is_json:
            data = request.get_json()
            prompt = data.get("prompt", "").strip() if data else ""
            
        else:
            prompt = request.form.get("prompt", "").strip()
            file = request.files.get("file")
        
        print("prompt", prompt)
        print("file", file)

        if not prompt and not file:
            return jsonify({"error": "Missing prompt/file"}), 400
        
        file_content = ""
        if file:
            try:
                file_content = extract_text_from_file(file)
            except Exception as e:
                return jsonify({"error": f"Failed to parse file: {str(e)}"}), 400
            
        if file_content:  # Case when a file is uploaded
            full_prompt = f"""Using this attached document, please answer this:
        {prompt}

        Uploaded document:
        \"\"\"
        {file_content.strip()}
        \"\"\""""

            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "system", "content": "You are a chatbot assistant for the company Anote. You should help the user to answer their question using the attached document."
                    },
                    {
                        "role": "user", "content": full_prompt.strip()
                    }
                ]
            )
        else:  # Case when no file is uploaded
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                {"role": "system", "content": "You are a chatbot assistant for the company Anote. You should help the user to answer their question."},
                {"role": "user", "content": prompt}
                ]
            )

        reply = completion.choices[0].message.content
        return jsonify({"response": reply})

    except Exception as e:
        import logging
        logging.error(f"[ERROR] {str(e)}", exc_info=True)
        return jsonify({"error": "An internal error has occurred"}), 500

handler = gpt4_blueprint