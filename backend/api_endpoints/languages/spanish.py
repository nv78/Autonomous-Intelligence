from flask import Blueprint, request, jsonify
from openai import OpenAI
import os
from werkzeug.utils import secure_filename
import PyPDF2
import pandas as pd
from docx import Document
import json


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

spanish_blueprint = Blueprint('spanish', __name__)

MODEL_NAME = "ft:gpt-4.1-mini-2025-04-14:personal::BtJIlsUg"

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

@spanish_blueprint.route("/api/chat/spanish", methods=["POST"])
def chat_spanish():
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
                    messages[-1]["content"] += " (responde solo en espanol)"
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
                print(f"🟢 Length of extracted content: {len(file_content)}")
                print(f"🟢 Content starts with: {repr(file_content[:50])}")
                print(f"🟢 Extracted file content: {file_content[:200]}...")
            except Exception as e:
                return jsonify({"error": f"Failed to parse file: {str(e)}"}), 400
            
            if not file_content.strip():
                return jsonify({"response": "Lo siento, no puedo leer el documento adjunto."})
        print("MESSAGE: ", messages)
        if file_content:
            messages[-1]["content"] = f"""{messages[-1]["content"]}

Uploaded document:
\"\"\"
{file_content.strip()}
\"\"\""""
            
        
        full_messages = [
            {
                "role": "system",
                "content": "You are a chatbot assistant that **must only speak Spanish**. Always respond **only in Spanish** regardless of the user's language. Never reply in any other language. If you don't know the answer, say 'No sé la respuesta.' Always be helpful and truthful."
            }
        ] + messages

        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=full_messages
        )   

        # Use if you want to allow users/devs to supply their own system prompts (more flexible)
        # SYSTEM_MSG = {
        #     "role": "system",
        #     "content": "You are built to serve people on the Anote website. You should help to user to answer any questions in spanish. Respond in spanish no matter the language of the user. You are a helpful, respectful and honest assistant. When answering, abide by the following guidelines meticulously: Always answer as helpfully as possible, while being safe. Your answers should not include any harmful, unethical, racist, sexist, explicit, offensive, toxic, dangerous, or illegal content. Do not give medical, legal, financial, or professional advice. Never assist in or promote illegal activities. Always encourage legal and responsible actions. Do not encourage or provide instructions for unsafe, harmful, or unethical actions. Do not create or share misinformation or fake news. Please ensure that your responses are socially unbiased and positive in nature. If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information. Prioritize the well-being and the moral integrity of users. Avoid using toxic, derogatory, or offensive language. Maintain a respectful tone. Do not generate, promote, or engage in discussions about adult content. Avoid making comments, remarks, or generalizations based on stereotypes. Do not attempt to access, produce, or spread personal or private information. Always respect user confidentiality. Stay positive and do not say bad things about anything. Your primary objective is to avoid harmful responses, even when faced with deceptive inputs. Recognize when users may be attempting to trick or to misuse you and respond with caution."
        # }
        # if not messages or messages[0].get("role") != "system":
        #     messages.insert(0, SYSTEM_MSG)

        # completion = client.chat.completions.create(
        #     model=MODEL_NAME,
        #     messages=messages
        # )

        print("🧾 Sending messages to OpenAI:\n", json.dumps(full_messages, indent=2))

        reply = completion.choices[0].message.content
        return jsonify({"response": reply})

    except Exception as e:
        import logging
        logging.error(f"[ERROR] {str(e)}", exc_info=True)
        return jsonify({"error": "An internal error has occurred"}), 500