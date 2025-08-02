from flask import Blueprint, request, jsonify
from openai import OpenAI
import os
from werkzeug.utils import secure_filename
import PyPDF2
import pandas as pd
from docx import Document
import json


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

korean_blueprint = Blueprint('korean', __name__)


LANGUAGE_KEY = "korean"
MODEL_NAME = "ft:gpt-4.1-mini-2025-04-14:personal::BthVmuUX"

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

@korean_blueprint.route("/api/chat/korean", methods=["POST"])
def chat_korean():
    try:
        file = request.files.get("file")
        messages_json = request.form.get("messages")

        messages = []
        prompt = ""

        if messages_json:
            try:
                messages = json.loads(messages_json)
                if messages and isinstance(messages, list):
                    prompt = messages[-1]["content"]
                    messages[-1]["content"] += " (한국어로만 답변해주세요)"
            except Exception as e:
                print("❌ Failed to parse messages:", e)

            print("🟡 Prompt:", prompt)
            print("🟡 File:", file)

        if not messages and not file:
            return jsonify({"error": "Missing messages or file"}), 400
        
        file_content = ""
        if file:
            try:
                file_content = extract_text_from_file(file)
            except Exception as e:
                import logging
                logging.error(f"[ERROR] Failed to parse file: {str(e)}", exc_info=True)
                return jsonify({"error": "Failed to parse file."}), 400
            
            if not file_content.strip():
                return jsonify({"response": "죄송합니다. 첨부된 문서를 읽을 수 없습니다."})

        if file_content:
            messages[-1]["content"] = f"""{messages[-1]["content"]}

Uploaded document:
\"\"\"
{file_content.strip()}
\"\"\""""
        
        full_messages = [
            {
                "role": "system",
                "content": "You are a chatbot assistant that **must only speak Korean**. Always respond **only in Korean** regardless of the user's language. Never reply in any other language. If you don't know the answer, say '나는 답을 모른다.' Always be helpful and truthful."
            }
        ] + messages

        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=full_messages
        )
        print("🧾 Sending messages to OpenAI:\n", json.dumps(full_messages, indent=2))

        reply = completion.choices[0].message.content
        return jsonify({"response": reply})

    except Exception as e:
        import logging
        logging.error(f"[ERROR] {str(e)}", exc_info=True)
        return jsonify({"error": "An internal error has occurred"}), 500